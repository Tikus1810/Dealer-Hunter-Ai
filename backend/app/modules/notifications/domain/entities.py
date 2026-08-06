"""Notifications domain entities (Band 11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class NotificationChannel(StrEnum):
    PUSH = "push"
    EMAIL = "email"


class NotificationEvent(StrEnum):
    SAVED_SEARCH_MATCH = "saved_search_match"
    PRICE_DROP = "price_drop"
    DEAL_SCORE_READY = "deal_score_ready"


class DevicePlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


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
    created_at: datetime | None = None


@dataclass(slots=True)
class DeviceToken:
    """A registered FCM device token (Band 11: push delivery target)."""

    id: uuid.UUID
    user_id: uuid.UUID
    token: str
    platform: DevicePlatform
    is_active: bool = True
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NotificationPreference:
    """One (event, channel) opt-in/out toggle for a user (Band 11: user
    opt-in/out). Absence of a row means "enabled" — see PreferenceResolver."""

    user_id: uuid.UUID
    event: NotificationEvent
    channel: NotificationChannel
    enabled: bool = True
