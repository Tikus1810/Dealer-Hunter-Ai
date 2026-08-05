"""RepairBrain REST endpoints (Band 06: "Add REST endpoints", Band 10: /api/v1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository
from app.modules.repair.application.service import RepairBrainService
from app.modules.repair.domain.entities import RepairReport
from app.modules.repair.infrastructure.repository import SqlAlchemyRepairReportRepository
from app.modules.repair.presentation.schemas import (
    RepairAnalysisRequest,
    RepairReportResponse,
    ReplacementPartResponse,
)

router = APIRouter(prefix="/api/v1/offers", tags=["repair-brain"])


def get_repair_brain_service(session: AsyncSession = Depends(get_db_session)) -> RepairBrainService:
    return RepairBrainService(
        offers=SqlAlchemyOfferRepository(session),
        repair_reports=SqlAlchemyRepairReportRepository(session),
    )


def _to_response(report: RepairReport) -> RepairReportResponse:
    return RepairReportResponse(
        offer_id=report.offer_id,
        repair_score=report.repair_score,
        estimated_repair_cost=report.estimated_repair_cost,
        estimated_repair_time_hours=report.estimated_repair_time_hours,
        difficulty=report.difficulty.value,
        required_tools=report.required_tools,
        compatible_parts=[
            ReplacementPartResponse(
                name=p.name, estimated_price=p.estimated_price, availability=p.availability
            )
            for p in report.compatible_parts
        ],
        risk_notes=report.risk_notes,
        summary=report.summary,
        report_version=report.report_version,
    )


@router.post("/{offer_id}/repair-report", response_model=RepairReportResponse)
async def create_repair_report(
    offer_id: uuid.UUID,
    body: RepairAnalysisRequest,
    service: RepairBrainService = Depends(get_repair_brain_service),
) -> RepairReportResponse:
    """Computes (and persists) a fresh report on every call — append-only
    history, not a cache, mirroring the DealBrain deal-score endpoint."""
    report = await service.analyze(offer_id, reported_defects=body.reported_defects)
    return _to_response(report)
