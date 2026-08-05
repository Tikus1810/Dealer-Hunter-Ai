"""Repair Scoring Engine (Band 06 architecture module).

Produces the 0-100 repair score: higher = clearer-cut / lower-risk / cheaper
repair. Deterministic — same faults/difficulty/cost in, same score out.

v1 weights are a documented starting point, not a spec-mandated formula —
Band 06 defines the output (0-100, explainable, versioned) but not a
concrete calculation. Tune alongside `report_version` once real repair
outcomes are available to validate against.
"""

from __future__ import annotations

from app.modules.repair.domain.catalog import difficulty_rank
from app.modules.repair.domain.entities import DetectedFault, RepairDifficulty

BASE_SCORE = 90.0
PER_FAULT_PENALTY = 8.0
PER_INFERRED_FAULT_PENALTY = 3.0
DIFFICULTY_PENALTY = {0: 0.0, 1: 10.0, 2: 25.0}  # keyed by difficulty_rank()
HIGH_COST_THRESHOLD = 300.0
HIGH_COST_PENALTY = 15.0
MODERATE_COST_THRESHOLD = 150.0
MODERATE_COST_PENALTY = 7.0

REPORT_VERSION = "1.0.0"


class RepairScoringEngine:
    def score(
        self, faults: list[DetectedFault], difficulty: RepairDifficulty, estimated_cost: float
    ) -> int:
        value = BASE_SCORE
        value -= len(faults) * PER_FAULT_PENALTY
        value -= sum(1 for f in faults if not f.is_confirmed) * PER_INFERRED_FAULT_PENALTY
        value -= DIFFICULTY_PENALTY[difficulty_rank(difficulty)]

        if estimated_cost > HIGH_COST_THRESHOLD:
            value -= HIGH_COST_PENALTY
        elif estimated_cost > MODERATE_COST_THRESHOLD:
            value -= MODERATE_COST_PENALTY

        return int(round(max(0.0, min(100.0, value))))
