"""SQLAlchemy implementation of `RepairReportRepositoryProtocol` (Band 03/09)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repair.domain.entities import RepairDifficulty, RepairReport, ReplacementPart
from app.modules.repair.infrastructure.models import RepairReportModel


def _to_entity(row: RepairReportModel) -> RepairReport:
    return RepairReport(
        offer_id=row.offer_id,
        repair_score=row.repair_score,
        estimated_repair_cost=float(row.estimated_repair_cost),
        estimated_repair_time_hours=float(row.estimated_repair_time_hours),
        difficulty=RepairDifficulty(row.difficulty),
        required_tools=list(row.required_tools),
        compatible_parts=[ReplacementPart(**part) for part in row.compatible_parts],
        risk_notes=list(row.risk_notes),
        summary=row.summary,
        report_version=row.report_version,
    )


class SqlAlchemyRepairReportRepository:
    """Implements `RepairReportRepositoryProtocol` (app.modules.repair.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: RepairReport) -> None:
        row = RepairReportModel(
            offer_id=report.offer_id,
            repair_score=report.repair_score,
            estimated_repair_cost=Decimal(str(report.estimated_repair_cost)),
            estimated_repair_time_hours=Decimal(str(report.estimated_repair_time_hours)),
            difficulty=report.difficulty,
            required_tools=report.required_tools,
            compatible_parts=[
                {
                    "name": p.name,
                    "estimated_price": p.estimated_price,
                    "availability": p.availability,
                }
                for p in report.compatible_parts
            ],
            risk_notes=report.risk_notes,
            summary=report.summary,
            report_version=report.report_version,
        )
        self._session.add(row)
        await self._session.flush()

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> RepairReport | None:
        stmt = (
            select(RepairReportModel)
            .where(RepairReportModel.offer_id == offer_id)
            .order_by(RepairReportModel.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(row) if row else None
