"""Notifications domain entities (Band 11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class NotificationChannel(StrEnum):
    PUSH = "push"
    EMAIL = "email"


class NotificationEvent(StrEnum):
    SAVED_SEARCH_MATCH = "saved_search_match"
    PRICE_DROP = "price_drop"
    DEAL_SCORE_READY = "deal_score_ready"


@dataclass(slots=True)
class Notification:
    id: uuid.UUID
    user_id: uuid.UUID
    event: NotificationEvent
    channel: NotificationChannel
    title: str
    body: str
    data: dict[str, Any] | None = None
    is_read: bool = False
