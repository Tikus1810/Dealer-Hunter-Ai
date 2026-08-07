"""Unit tests for Vision AI's domain components and service.

`ObservationEngine` tests use real in-memory Pillow images (generated, not
fetched) — no network calls. `ImagePreprocessor`/service tests mock HTTP
via respx.
"""

from __future__ import annotations

import io
import uuid

import httpx
import pytest
import respx
from PIL import Image, ImageFilter

from app.core.exceptions import NotFoundError
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.vision.domain.confidence import (
    INCOMPLETE_SET_CONFIDENCE_PENALTY,
    MIN_IMAGES_FOR_COMPLETE_SET,
    ConfidenceEstimator,
)
from app.modules.vision.domain.entities import ImageQualityObservation
from app.modules.vision.domain.formatter import OutputFormatter
from app.modules.vision.domain.observation_engine import ObservationEngine
from app.modules.vision.infrastructure.image_preprocessor import ImageFetchError, ImagePreprocessor


def _sharp_image() -> Image.Image:
    # High-frequency checkerboard pattern -> strong edges -> high variance.
    image = Image.new("RGB", (800, 600))
    for x in range(800):
        for y in range(0, 600, 40):
            color = (255, 255, 255) if (x // 20) % 2 == 0 else (0, 0, 0)
            for dy in range(20):
                image.putpixel((x, y + dy), color)
    return image


def _blurry_image() -> Image.Image:
    # Heavily Gaussian-blurred version of the sharp checkerboard — a
    # realistic stand-in for an out-of-focus photo, not just a flat swatch.
    return _sharp_image().filter(ImageFilter.GaussianBlur(radius=20))


def _flat_image() -> Image.Image:
    return Image.new("RGB", (800, 600), color=(120, 120, 120))


def _small_image() -> Image.Image:
    return Image.new("RGB", (100, 80), color=(200, 200, 200))


class TestObservationEngine:
    def test_sharp_image_is_not_flagged_blurry(self) -> None:
        obs = ObservationEngine().assess("https://x/1.jpg", _sharp_image())
        assert obs.is_blurry is False
        assert obs.is_reachable is True

    def test_gaussian_blurred_image_is_flagged_blurry(self) -> None:
        obs = ObservationEngine().assess("https://x/1.jpg", _blurry_image())
        assert obs.is_blurry is True

    def test_flat_featureless_image_is_flagged_blurry(self) -> None:
        obs = ObservationEngine().assess("https://x/1.jpg", _flat_image())
        assert obs.is_blurry is True

    def test_small_image_is_flagged_low_resolution(self) -> None:
        obs = ObservationEngine().assess("https://x/1.jpg", _small_image())
        assert obs.is_low_resolution is True
        assert obs.resolution == (100, 80)

    def test_deterministic_for_identical_input(self) -> None:
        image = _sharp_image()
        engine = ObservationEngine()
        first = engine.assess("https://x/1.jpg", image)
        second = engine.assess("https://x/1.jpg", image)
        assert first == second


class TestConfidenceEstimator:
    def test_no_images_zero_confidence(self) -> None:
        assert ConfidenceEstimator().estimate([]) == 0.0

    def test_all_unreachable_zero_confidence(self) -> None:
        obs = [
            ImageQualityObservation("u1", False, None, None, None, "fail"),
            ImageQualityObservation("u2", False, None, None, None, "fail"),
        ]
        assert ConfidenceEstimator().estimate(obs) == 0.0

    def test_all_good_images_high_confidence_when_set_complete(self) -> None:
        obs = [
            ImageQualityObservation(f"u{i}", True, False, (800, 600), False, "ok")
            for i in range(MIN_IMAGES_FOR_COMPLETE_SET)
        ]
        assert ConfidenceEstimator().estimate(obs) == 1.0

    def test_incomplete_set_is_penalized(self) -> None:
        obs = [ImageQualityObservation("u1", True, False, (800, 600), False, "ok")]
        confidence = ConfidenceEstimator().estimate(obs)
        assert confidence == round(1.0 * INCOMPLETE_SET_CONFIDENCE_PENALTY, 2)

    def test_mixed_quality_scales_between_0_and_1(self) -> None:
        obs = [
            ImageQualityObservation("u1", True, False, (800, 600), False, "ok"),
            ImageQualityObservation("u2", True, True, (800, 600), False, "blurry"),
            ImageQualityObservation("u3", True, False, (800, 600), False, "ok"),
        ]
        confidence = ConfidenceEstimator().estimate(obs)
        assert 0.0 < confidence < 1.0


class TestOutputFormatter:
    def test_flags_incomplete_set_below_minimum(self) -> None:
        result = OutputFormatter().format(uuid.uuid4(), 1, [], 0.5)
        assert result.is_image_set_incomplete is True

    def test_complete_set_not_flagged(self) -> None:
        result = OutputFormatter().format(uuid.uuid4(), MIN_IMAGES_FOR_COMPLETE_SET, [], 0.9)
        assert result.is_image_set_incomplete is False

    def test_cosmetic_condition_is_explicitly_not_available(self) -> None:
        result = OutputFormatter().format(uuid.uuid4(), 3, [], 0.5)
        assert result.cosmetic_condition == "not_available"
        assert result.cosmetic_condition_note

    def test_cosmetic_assessment_populates_real_fields_when_provided(self) -> None:
        from app.modules.vision.domain.entities import CosmeticAssessment

        cosmetic = CosmeticAssessment(
            condition="good",
            confidence=0.8,
            observed_damage=["scuff on lid"],
            uncertain_notes=[],
            missing_components=["charger"],
            reasoning="Light wear visible in photos.",
            model_used="claude-opus-5",
            prompt_version="1.0.0",
        )
        result = OutputFormatter().format(uuid.uuid4(), 3, [], 0.5, cosmetic)
        assert result.cosmetic_condition == "good"
        assert result.cosmetic_condition_note == "Light wear visible in photos."
        assert result.missing_components == ["charger"]
        assert result.cosmetic_model_used == "claude-opus-5"
        assert result.cosmetic_prompt_version == "1.0.0"

    def test_cosmetic_model_provenance_is_none_when_no_analyzer_ran(self) -> None:
        result = OutputFormatter().format(uuid.uuid4(), 3, [], 0.5)
        assert result.cosmetic_model_used is None
        assert result.cosmetic_prompt_version is None


class TestImagePreprocessor:
    @respx.mock
    async def test_fetch_and_decode_returns_pil_image(self) -> None:
        buffer = io.BytesIO()
        _sharp_image().save(buffer, format="PNG")
        respx.get("https://x/1.jpg").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )

        async with httpx.AsyncClient() as client:
            preprocessor = ImagePreprocessor(http_client=client)
            image = await preprocessor.fetch_and_decode("https://x/1.jpg")

        assert image.size == (800, 600)

    @respx.mock
    async def test_fetch_failure_raises_image_fetch_error(self) -> None:
        respx.get("https://x/missing.jpg").mock(return_value=httpx.Response(404))

        async with httpx.AsyncClient() as client:
            preprocessor = ImagePreprocessor(http_client=client)
            with pytest.raises(ImageFetchError):
                await preprocessor.fetch_and_decode("https://x/missing.jpg")

    @respx.mock
    async def test_non_image_content_raises_image_fetch_error(self) -> None:
        respx.get("https://x/notanimage").mock(
            return_value=httpx.Response(200, content=b"not an image")
        )

        async with httpx.AsyncClient() as client:
            preprocessor = ImagePreprocessor(http_client=client)
            with pytest.raises(ImageFetchError):
                await preprocessor.fetch_and_decode("https://x/notanimage")


class FakeOfferRepository:
    def __init__(self, offers: list[Offer]) -> None:
        self._offers = {o.id: o for o in offers}

    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        return self._offers.get(offer_id)

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool:
        raise NotImplementedError

    async def upsert(self, offer: Offer) -> Offer:
        raise NotImplementedError

    async def list_by_category(
        self, category: str, *, page: int = 1, page_size: int = 20
    ) -> list[Offer]:
        raise NotImplementedError

    async def count_by_category(self, category: str) -> int:
        raise NotImplementedError


def _offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": "1",
        "title": "MacBook Pro",
        "description": "desc",
        "price_amount": 900.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "images": ["https://x/1.jpg", "https://x/2.jpg"],
        "url": "https://ebay.de/itm/1",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


class TestVisionAnalysisService:
    async def test_analyze_raises_not_found_for_unknown_offer(self) -> None:
        from app.modules.vision.application.service import VisionAnalysisService

        service = VisionAnalysisService(FakeOfferRepository([]))
        with pytest.raises(NotFoundError):
            await service.analyze(uuid.uuid4())

    @respx.mock
    async def test_analyze_handles_mixed_reachable_and_unreachable_images(self) -> None:
        from app.modules.vision.application.service import VisionAnalysisService

        buffer = io.BytesIO()
        _sharp_image().save(buffer, format="PNG")
        respx.get("https://x/1.jpg").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )
        respx.get("https://x/2.jpg").mock(return_value=httpx.Response(404))

        offer = _offer()
        service = VisionAnalysisService(FakeOfferRepository([offer]))

        result = await service.analyze(offer.id)

        assert result.image_count == 2
        assert result.is_image_set_incomplete is True  # only 2 < MIN_IMAGES_FOR_COMPLETE_SET
        reachable = [o for o in result.per_image if o.is_reachable]
        unreachable = [o for o in result.per_image if not o.is_reachable]
        assert len(reachable) == 1
        assert len(unreachable) == 1
        assert result.cosmetic_condition == "not_available"

    async def test_analyze_with_no_images_yields_zero_confidence(self) -> None:
        from app.modules.vision.application.service import VisionAnalysisService

        offer = _offer(images=[])
        service = VisionAnalysisService(FakeOfferRepository([offer]))

        result = await service.analyze(offer.id)

        assert result.image_count == 0
        assert result.confidence == 0.0
        assert result.is_image_set_incomplete is True

    @respx.mock
    async def test_analyze_uses_cosmetic_analyzer_when_configured(self) -> None:
        from app.modules.vision.application.service import VisionAnalysisService
        from app.modules.vision.domain.entities import CosmeticAssessment

        buffer = io.BytesIO()
        _sharp_image().save(buffer, format="PNG")
        respx.get("https://x/1.jpg").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )
        respx.get("https://x/2.jpg").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )

        class FakeCosmeticAnalyzer:
            def __init__(self) -> None:
                self.called_with: list[str] | None = None

            async def analyze(
                self, image_urls: list[str], *, category_hint: str
            ) -> CosmeticAssessment:
                self.called_with = image_urls
                return CosmeticAssessment(
                    condition="good",
                    confidence=1.0,
                    observed_damage=[],
                    uncertain_notes=[],
                    missing_components=[],
                    reasoning="Looks fine.",
                    model_used="fake-model",
                    prompt_version="1.0.0",
                )

        cosmetic_analyzer = FakeCosmeticAnalyzer()
        offer = _offer()
        service = VisionAnalysisService(
            FakeOfferRepository([offer]), cosmetic_analyzer=cosmetic_analyzer
        )

        result = await service.analyze(offer.id)

        assert result.cosmetic_condition == "good"
        assert result.cosmetic_condition_note == "Looks fine."
        assert cosmetic_analyzer.called_with == offer.images
        assert result.cosmetic_model_used == "fake-model"
        assert result.cosmetic_prompt_version == "1.0.0"

    @respx.mock
    async def test_analyze_falls_back_gracefully_when_cosmetic_analyzer_fails(self) -> None:
        from app.modules.vision.application.service import VisionAnalysisService
        from app.modules.vision.domain.entities import CosmeticAssessment

        buffer = io.BytesIO()
        _sharp_image().save(buffer, format="PNG")
        respx.get("https://x/1.jpg").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )
        respx.get("https://x/2.jpg").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )

        class FailingCosmeticAnalyzer:
            async def analyze(
                self, image_urls: list[str], *, category_hint: str
            ) -> CosmeticAssessment:
                raise RuntimeError("boom")

        offer = _offer()
        service = VisionAnalysisService(
            FakeOfferRepository([offer]), cosmetic_analyzer=FailingCosmeticAnalyzer()
        )

        result = await service.analyze(offer.id)

        assert result.cosmetic_condition == "not_available"
        assert result.confidence > 0.0  # quality confidence still computed
