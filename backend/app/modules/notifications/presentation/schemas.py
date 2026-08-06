"""Pydantic v2 DTOs for the Notifications API (Band 10/11)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.modules.notifications.domain.entities import (
    DevicePlatform,
    NotificationChannel,
    NotificationEvent,
)


class RegisterDeviceRequest(BaseModel):
    token: str
    platform: DevicePlatform


class UnregisterDeviceRequest(BaseModel):
    token: str


class DeviceTokenResponse(BaseModel):
    id: uuid.UUID
    token: str
    platform: DevicePlatform
    is_active: bool


class NotificationResponse(BaseModel):
    id: uuid.UUID
    event: NotificationEvent
    channel: NotificationChannel
    title: str
    body: str
    data: dict[str, Any] | None
    is_read: bool
    created_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class NotificationPreferenceResponse(BaseModel):
    event: NotificationEvent
    channel: NotificationChannel
    enabled: bool


class SetNotificationPreferenceRequest(BaseModel):
    event: NotificationEvent
    channel: NotificationChannel
    enabled: bool
