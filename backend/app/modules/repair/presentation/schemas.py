"""Pydantic v2 DTOs for the RepairBrain API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RepairAnalysisRequest(BaseModel):
    reported_defects: list[str] = Field(default_factory=list, max_length=20)


class ReplacementPartResponse(BaseModel):
    name: str
    estimated_price: float
    availability: str


class RepairReportResponse(BaseModel):
    offer_id: uuid.UUID
    repair_score: int
    estimated_repair_cost: float
    estimated_repair_time_hours: float
    difficulty: str
    required_tools: list[str]
    compatible_parts: list[ReplacementPartResponse]
    risk_notes: list[str]
    summary: str
    report_version: str
