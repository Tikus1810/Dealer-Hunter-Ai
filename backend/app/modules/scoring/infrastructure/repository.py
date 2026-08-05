"""SQLAlchemy implementation of `DealScoreRepositoryProtocol` (Band 03/09)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scoring.domain.entities import DealScoreResult, ExplanationFactor
from app.modules.scoring.infrastructure.models import DealScoreModel


def _to_entity(row: DealScoreModel) -> DealScoreResult:
    return DealScoreResult(
        offer_id=row.offer_id,
        score=row.score,
        confidence=float(row.confidence),
        estimated_market_value=float(row.estimated_market_value),
        estimated_total_cost=float(row.estimated_total_cost),
        recommendation=row.recommendation,
        explanation=[ExplanationFactor(**factor) for factor in row.explanation],
        scoring_version=row.scoring_version,
    )


class SqlAlchemyDealScoreRepository:
    """Implements `DealScoreRepositoryProtocol` (app.modules.scoring.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, result: DealScoreResult) -> None:
        row = DealScoreModel(
            offer_id=result.offer_id,
            score=result.score,
            confidence=Decimal(str(result.confidence)),
            estimated_market_value=Decimal(str(result.estimated_market_value)),
            estimated_total_cost=Decimal(str(result.estimated_total_cost)),
            recommendation=result.recommendation,
            explanation=[
                {"name": f.name, "impact": f.impact, "description": f.description}
                for f in result.explanation
            ],
            scoring_version=result.scoring_version,
        )
        self._session.add(row)
        await self._session.flush()

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> DealScoreResult | None:
        stmt = (
            select(DealScoreModel)
            .where(DealScoreModel.offer_id == offer_id)
            .order_by(DealScoreModel.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(row) if row else None
