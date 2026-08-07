"""Pydantic v2 DTOs for the Analytics API (Band 15)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Property values are restricted to JSON primitives — no nested objects/
# arrays. Keeps analytics properties genuinely flat/queryable (Band 15:
# "aggregation") and, as a side effect, rules out a client smuggling
# arbitrarily-structured (and therefore harder-to-audit-for-PII) data in.
PropertyValue = str | int | float | bool | None


class TrackEventRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    properties: dict[str, PropertyValue] = Field(default_factory=dict)


class AnalyticsEventResponse(BaseModel):
    id: uuid.UUID
    name: str
    user_id: uuid.UUID | None
    properties: dict[str, Any]
    occurred_at: datetime | None


class AnalyticsSummaryResponse(BaseModel):
    event_name: str
    count: int
    distinct_users: int
    since: datetime | None
