"""Time Estimator (Band 06 architecture module). Also determines overall
difficulty, since both are direct functions of which faults were found —
the more severe fault in a batch sets the ceiling for both.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.repair.domain.catalog import (
    DEFAULT_FAULT_DIFFICULTY,
    DEFAULT_FAULT_TIME_HOURS,
    FAULT_DIFFICULTY,
    FAULT_TIME_HOURS,
    difficulty_rank,
)
from app.modules.repair.domain.entities import DetectedFault, RepairDifficulty


@dataclass(frozen=True, slots=True)
class TimeEstimate:
    hours: float
    difficulty: RepairDifficulty


class TimeEstimator:
    def estimate(self, faults: list[DetectedFault]) -> TimeEstimate:
        if not faults:
            return TimeEstimate(hours=0.0, difficulty=RepairDifficulty.BEGINNER)

        total_hours = sum(
            FAULT_TIME_HOURS.get(f.category, DEFAULT_FAULT_TIME_HOURS) for f in faults
        )
        hardest = max(
            (FAULT_DIFFICULTY.get(f.category, DEFAULT_FAULT_DIFFICULTY) for f in faults),
            key=difficulty_rank,
        )
        return TimeEstimate(hours=round(total_hours, 2), difficulty=hardest)
