"""Scoring (DealBrain) domain entities (Band 05)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ExplanationFactor:
    """One human-readable factor that contributed to the score (Band 05: no hidden rules)."""

    name: str
    impact: float  # signed contribution to the final score
    description: str


@dataclass(frozen=True, slots=True)
class DealScoreResult:
    offer_id: uuid.UUID
    score: int  # 0-100
    confidence: float  # 0.0-1.0
    estimated_market_value: float
    estimated_total_cost: float
    recommendation: str
    explanation: list[ExplanationFactor] = field(default_factory=list)
    scoring_version: str = "1.0.0"
