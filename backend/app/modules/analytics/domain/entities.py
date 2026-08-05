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
