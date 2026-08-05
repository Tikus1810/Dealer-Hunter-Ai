"""Cost Estimator (Band 06 architecture module). Pure arithmetic — parts
price sum plus indicative labor cost. No live pricing source (see
`catalog.py`'s module docstring)."""

from __future__ import annotations

from app.modules.repair.domain.entities import ReplacementPart

LABOR_RATE_PER_HOUR = 35.0  # EUR, indicative flat rate


class CostEstimator:
    def estimate(self, parts: list[ReplacementPart], time_hours: float) -> float:
        parts_cost = sum(p.estimated_price for p in parts)
        labor_cost = time_hours * LABOR_RATE_PER_HOUR
        return round(parts_cost + labor_cost, 2)
