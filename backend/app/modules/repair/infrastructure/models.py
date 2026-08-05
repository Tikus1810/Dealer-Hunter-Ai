"""SQLAlchemy model for the `repair` (RepairBrain) module (Band 09).

Append-only per offer, mirroring the DealScore versioning rationale."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.modules.repair.domain.entities import RepairDifficulty


class RepairReportModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "repair_reports"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repair_score: Mapped[int] = mapped_column(nullable=False)
    estimated_repair_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_repair_time_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    difficulty: Mapped[RepairDifficulty] = mapped_column(
        Enum(RepairDifficulty, native_enum=False, length=20, validate_strings=True), nullable=False
    )
    required_tools: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)), default=list, nullable=False
    )
    compatible_parts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    risk_notes: Mapped[list[str]] = mapped_column(ARRAY(String(300)), default=list, nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    report_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
