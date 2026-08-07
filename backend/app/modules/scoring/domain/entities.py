"""Scoring (DealBrain) domain entities (Band 05)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.ai_rules import validate_confidence, validate_score


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

    def __post_init__(self) -> None:
        # Band 16: AI Rules — this entity refuses to exist out of bounds,
        # regardless of how it was constructed (ScoringEngine.combine()
        # already clamps on its way out; this is the backstop for every
        # other way a DealScoreResult could get built).
        validate_score("score", self.score)
        validate_confidence("confidence", self.confidence)


@dataclass(frozen=True, slots=True)
class AnalyzerOutput:
    """One analyzer's contribution before the Scoring Engine combines them
    (Band 05 architecture: each analyzer module is independently testable
    and returns its own explanation factors — never a bare number)."""

    score_contribution: float  # signed points added to/subtracted from the base score
    confidence: float  # 0.0-1.0 — this analyzer's confidence in its own contribution
    factors: list[ExplanationFactor] = field(default_factory=list)

    def __post_init__(self) -> None:
        # `score_contribution` is deliberately NOT range-checked here — it's
        # an unbounded signed delta by design (see ScoringEngine.combine,
        # which sums every analyzer's contribution before clamping the
        # *final* score to 0-100). Only `confidence` has a fixed range.
        validate_confidence("confidence", self.confidence)
