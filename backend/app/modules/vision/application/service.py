"""Vision AI application service — implements `VisionAnalysisServiceProtocol`.

Orchestrates: Image Preprocessor (fetch/decode, I/O) -> Observation Engine
(pure per-image assessment) -> Confidence Estimator -> [optional Claude
Vision cosmetic-condition analysis] -> Output Formatter. A fetch/decode
failure for one image becomes an "unreachable" observation, not an aborted
analysis (Band 08: no I/O failure should invalidate the rest of the image
set) — and the same applies to the cosmetic analyzer: its failure falls
back to "not_available" rather than failing the whole request.
"""

from __future__ import annotations

import asyncio
import uuid

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.modules.offers.application.interfaces import OfferRepositoryProtocol
from app.modules.vision.application.interfaces import CosmeticConditionAnalyzerProtocol
from app.modules.vision.domain.confidence import ConfidenceEstimator
from app.modules.vision.domain.entities import ImageQualityObservation, VisionObservation
from app.modules.vision.domain.formatter import OutputFormatter
from app.modules.vision.domain.observation_engine import ObservationEngine
from app.modules.vision.infrastructure.image_preprocessor import ImageFetchError, ImagePreprocessor

logger = get_logger(__name__)


class VisionAnalysisService:
    def __init__(
        self,
        offers: OfferRepositoryProtocol,
        *,
        preprocessor: ImagePreprocessor | None = None,
        observation_engine: ObservationEngine | None = None,
        confidence_estimator: ConfidenceEstimator | None = None,
        output_formatter: OutputFormatter | None = None,
        cosmetic_analyzer: CosmeticConditionAnalyzerProtocol | None = None,
    ) -> None:
        self._offers = offers
        self._preprocessor = preprocessor or ImagePreprocessor()
        self._observation_engine = observation_engine or ObservationEngine()
        self._confidence_estimator = confidence_estimator or ConfidenceEstimator()
        self._output_formatter = output_formatter or OutputFormatter()
        self._cosmetic_analyzer = cosmetic_analyzer

    async def analyze(self, offer_id: uuid.UUID) -> VisionObservation:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            raise NotFoundError("offer not found", details={"offer_id": str(offer_id)})

        per_image = await asyncio.gather(*(self._assess_one(url) for url in offer.images))
        quality_confidence = self._confidence_estimator.estimate(list(per_image))

        cosmetic = None
        confidence = quality_confidence
        if self._cosmetic_analyzer is not None and offer.images:
            reachable_urls = [obs.image_url for obs in per_image if obs.is_reachable]
            try:
                cosmetic = await self._cosmetic_analyzer.analyze(
                    reachable_urls or offer.images, category_hint=offer.category.value
                )
                confidence = round((quality_confidence + cosmetic.confidence) / 2, 2)
            except Exception as exc:  # noqa: BLE001 — cosmetic analysis is best-effort
                logger.warning("cosmetic_analysis_failed", offer_id=str(offer_id), error=str(exc))

        return self._output_formatter.format(
            offer.id, len(offer.images), list(per_image), confidence, cosmetic
        )

    async def _assess_one(self, image_url: str) -> ImageQualityObservation:
        try:
            image = await self._preprocessor.fetch_and_decode(image_url)
        except ImageFetchError as exc:
            return ImageQualityObservation(
                image_url=image_url,
                is_reachable=False,
                is_blurry=None,
                resolution=None,
                is_low_resolution=None,
                note=str(exc),
            )
        return self._observation_engine.assess(image_url, image)
