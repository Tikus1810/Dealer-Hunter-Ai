"""Analytics domain entities (Band 15)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AnalyticsEvent:
    id: uuid.UUID
    name: str
    user_id: uuid.UUID | None
    properties: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    """Aggregate counts for one event name over a time window — the
    building block `GET /api/v1/analytics/summary` returns. Deliberately
    just two numbers (Band 15: KPIs) rather than a wider metrics surface:
    total volume and reach (distinct users) already answer the two
    questions every other KPI in a v1 product analytics setup derives
    from ("how much" and "how many people")."""

    event_name: str
    count: int
    distinct_users: int
    since: datetime | None
