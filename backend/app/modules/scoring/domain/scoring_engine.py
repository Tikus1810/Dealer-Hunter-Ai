"""DealBrain Scoring Engine (Band 05 architecture module): combines analyzer
outputs into a final `DealScoreResult`. Pure and deterministic — same
`AnalyzerOutput` list in, same result out, every time.
"""

from __future__ import annotations

from app.modules.offers.domain.entities import Offer
from app.modules.scoring.domain.entities import AnalyzerOutput, DealScoreResult

BASE_SCORE = 50.0
SCORING_VERSION = "1.0.0"


class ScoringEngine:
    def combine(
        self,
        offer: Offer,
        outputs: list[AnalyzerOutput],
        *,
        estimated_market_value: float,
        estimated_total_cost: float,
    ) -> DealScoreResult:
        raw_score = BASE_SCORE + sum(o.score_contribution for o in outputs)
        score = int(round(max(0.0, min(100.0, raw_score))))

        confidences = [o.confidence for o in outputs]
        confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

        factors = [factor for output in outputs for factor in output.factors]

        return DealScoreResult(
            offer_id=offer.id,
            score=score,
            confidence=confidence,
            estimated_market_value=round(estimated_market_value, 2),
            estimated_total_cost=round(estimated_total_cost, 2),
            recommendation="",  # filled in by ExplanationGenerator.finalize()
            explanation=factors,
            scoring_version=SCORING_VERSION,
        )
