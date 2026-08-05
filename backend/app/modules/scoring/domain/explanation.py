"""Explanation Generator (Band 05 architecture module): derives the
human-readable recommendation label and orders explanation factors so the
most decisive reasons come first.
"""

from __future__ import annotations

from dataclasses import replace

from app.modules.scoring.domain.entities import DealScoreResult

# Checked high-to-low; keep sorted descending by threshold.
_RECOMMENDATION_BANDS: tuple[tuple[int, str], ...] = (
    (80, "Strong Buy"),
    (65, "Good Deal"),
    (50, "Fair Deal"),
    (35, "Below Average"),
    (0, "Avoid"),
)


class ExplanationGenerator:
    def recommendation_for(self, score: int) -> str:
        for threshold, label in _RECOMMENDATION_BANDS:
            if score >= threshold:
                return label
        return "Avoid"

    def finalize(self, result: DealScoreResult) -> DealScoreResult:
        sorted_factors = sorted(result.explanation, key=lambda f: abs(f.impact), reverse=True)
        return replace(
            result, recommendation=self.recommendation_for(result.score), explanation=sorted_factors
        )
