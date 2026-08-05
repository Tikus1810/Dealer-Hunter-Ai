"""DealBrain REST endpoints (Band 05: "Expose REST endpoints through the
backend", Band 10: /api/v1). Read-only browsing stays unauthenticated for
now, matching the offers module — revisit in Task #15 (Security) if that
needs to change.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository
from app.modules.scoring.application.service import DealBrainService
from app.modules.scoring.domain.entities import DealScoreResult
from app.modules.scoring.infrastructure.repository import SqlAlchemyDealScoreRepository
from app.modules.scoring.presentation.schemas import DealScoreResponse, ExplanationFactorResponse

router = APIRouter(prefix="/api/v1/offers", tags=["deal-brain"])


def get_deal_brain_service(session: AsyncSession = Depends(get_db_session)) -> DealBrainService:
    return DealBrainService(
        offers=SqlAlchemyOfferRepository(session),
        deal_scores=SqlAlchemyDealScoreRepository(session),
    )


def _to_response(result: DealScoreResult) -> DealScoreResponse:
    return DealScoreResponse(
        offer_id=result.offer_id,
        score=result.score,
        confidence=result.confidence,
        estimated_market_value=result.estimated_market_value,
        estimated_total_cost=result.estimated_total_cost,
        recommendation=result.recommendation,
        explanation=[
            ExplanationFactorResponse(name=f.name, impact=f.impact, description=f.description)
            for f in result.explanation
        ],
        scoring_version=result.scoring_version,
    )


@router.get("/{offer_id}/deal-score", response_model=DealScoreResponse)
async def get_deal_score(
    offer_id: uuid.UUID, service: DealBrainService = Depends(get_deal_brain_service)
) -> DealScoreResponse:
    """Computes (and persists) a fresh score on every call. Scores are
    append-only history, not a cache — see `DealScoreModel`'s docstring."""
    result = await service.score_offer(offer_id)
    return _to_response(result)
