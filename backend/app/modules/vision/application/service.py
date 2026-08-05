"""Vision AI application service — implements `VisionAnalysisServiceProtocol`.

Orchestrates: Image Preprocessor (fetch/decode, I/O) -> Observation Engine
(pure per-image assessment) -> Confidence Estimator -> Output Formatter.
A fetch/decode failure for one image becomes an "unreachable" observation,
not an aborted analysis (Band 08: no I/O failure should invalidate the
rest of the image set).
"""

from __future__ import annotations

import asyncio
import uuid

from app.core.exceptions import NotFoundError
from app.modules.offers.application.interfaces import OfferRepositoryProtocol
from app.modules.vision.domain.confidence import ConfidenceEstimator
from app.modules.vision.domain.entities import ImageQualityObservation, VisionObservation
from app.modules.vision.domain.formatter import OutputFormatter
from app.modules.vision.domain.observation_engine import ObservationEngine
from app.modules.vision.infrastructure.image_preprocessor import ImageFetchError, ImagePreprocessor


class VisionAnalysisService:
    def __init__(
        self,
        offers: OfferRepositoryProtocol,
        *,
        preprocessor: ImagePreprocessor | None = None,
        observation_engine: ObservationEngine | None = None,
        confidence_estimator: ConfidenceEstimator | None = None,
        output_formatter: OutputFormatter | None = None,
    ) -> None:
        self._offers = offers
        self._preprocessor = preprocessor or ImagePreprocessor()
        self._observation_engine = observation_engine or ObservationEngine()
        self._confidence_estimator = confidence_estimator or ConfidenceEstimator()
        self._output_formatter = output_formatter or OutputFormatter()

    async def analyze(self, offer_id: uuid.UUID) -> VisionObservation:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            raise NotFoundError("offer not found", details={"offer_id": str(offer_id)})

        per_image = await asyncio.gather(
            *(self._assess_one(url) for url in offer.images)
        )
        confidence = self._confidence_estimator.estimate(list(per_image))

        return self._output_formatter.format(
            offer.id, len(offer.images), list(per_image), confidence
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
