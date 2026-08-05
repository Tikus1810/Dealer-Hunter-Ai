"""Pydantic v2 DTOs for the DealBrain API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ExplanationFactorResponse(BaseModel):
    name: str
    impact: float
    description: str


class DealScoreResponse(BaseModel):
    offer_id: uuid.UUID
    score: int
    confidence: float
    estimated_market_value: float
    estimated_total_cost: float
    recommendation: str
    explanation: list[ExplanationFactorResponse]
    scoring_version: str
