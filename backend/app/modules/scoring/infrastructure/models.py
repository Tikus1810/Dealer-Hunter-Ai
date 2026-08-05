"""SQLAlchemy model for the `scoring` (DealBrain) module (Band 09).

Deal scores are append-only (one row per scoring run) rather than a single
mutable row per offer, so score history is preserved as `scoring_version`
evolves (Band 05: "Scores are versioned for future improvements")."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class DealScoreModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_scores"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    estimated_market_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(60), nullable=False)
    explanation: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
