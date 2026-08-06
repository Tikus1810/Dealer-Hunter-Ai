"""Vision AI REST endpoints (Band 08: "Expose results through backend
interfaces", Band 10: /api/v1).

Compute-only for v1 — no persistence table exists for vision observations
yet (Band 09's schema didn't include one); add one if/when DealBrain or
RepairBrain start consuming stored observations instead of calling this
endpoint directly.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository
from app.modules.vision.application.interfaces import CosmeticConditionAnalyzerProtocol
from app.modules.vision.application.service import VisionAnalysisService
from app.modules.vision.domain.entities import VisionObservation
from app.modules.vision.infrastructure.claude_vision_provider import (
    ClaudeCosmeticConditionAnalyzer,
)
from app.modules.vision.presentation.schemas import (
    ImageQualityObservationResponse,
    VisionObservationResponse,
)

router = APIRouter(prefix="/api/v1/offers", tags=["vision-ai"])


def get_vision_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> VisionAnalysisService:
    cosmetic_analyzer: CosmeticConditionAnalyzerProtocol | None = (
        ClaudeCosmeticConditionAnalyzer(settings) if settings.anthropic_api_key else None
    )
    return VisionAnalysisService(
        offers=SqlAlchemyOfferRepository(session), cosmetic_analyzer=cosmetic_analyzer
    )


def _to_response(observation: VisionObservation) -> VisionObservationResponse:
    return VisionObservationResponse(
        offer_id=observation.offer_id,
        image_count=observation.image_count,
        is_image_set_incomplete=observation.is_image_set_incomplete,
        per_image=[
            ImageQualityObservationResponse(
                image_url=o.image_url,
                is_reachable=o.is_reachable,
                is_blurry=o.is_blurry,
                resolution=o.resolution,
                is_low_resolution=o.is_low_resolution,
                note=o.note,
            )
            for o in observation.per_image
        ],
        cosmetic_condition=observation.cosmetic_condition,
        cosmetic_condition_note=observation.cosmetic_condition_note,
        missing_components=observation.missing_components,
        confidence=observation.confidence,
        observation_version=observation.observation_version,
    )


@router.get("/{offer_id}/vision-observation", response_model=VisionObservationResponse)
async def get_vision_observation(
    offer_id: uuid.UUID, service: VisionAnalysisService = Depends(get_vision_service)
) -> VisionObservationResponse:
    observation = await service.analyze(offer_id)
    return _to_response(observation)
