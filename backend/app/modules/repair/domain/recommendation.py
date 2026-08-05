"""Recommendation Generator (Band 06 architecture module).

Produces the human-readable `summary` and `risk_notes` (Band 06 functional
requirement: "Mark uncertain estimates clearly" — every inferred-not-
confirmed fault gets its own risk note).
"""

from __future__ import annotations

from app.modules.repair.domain.entities import DetectedFault, RepairDifficulty


class RecommendationGenerator:
    def summarize(
        self,
        faults: list[DetectedFault],
        difficulty: RepairDifficulty,
        repair_score: int,
        estimated_cost: float,
        estimated_time_hours: float,
    ) -> tuple[str, list[str]]:
        risk_notes = [
            f"Fault '{f.category}' was inferred from listing text ('{f.detail}'), "
            "not explicitly confirmed by the seller."
            for f in faults
            if not f.is_confirmed
        ]
        if not faults:
            risk_notes.append("No faults reported or detected — repair need is unknown.")

        if repair_score >= 70:
            verdict = "Repair is likely worthwhile"
        elif repair_score >= 40:
            verdict = "Repair may be worthwhile depending on the final purchase price"
        else:
            verdict = "Repair is likely not worthwhile"

        fault_list = ", ".join(sorted({f.category for f in faults})) or "no specific faults"
        summary = (
            f"{verdict}: {len(faults)} fault(s) detected ({fault_list}), "
            f"difficulty {difficulty.value}, estimated cost {estimated_cost:.0f}, "
            f"estimated time {estimated_time_hours:.1f}h."
        )
        return summary, risk_notes
