"""Public interface of the `notifications` module."""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from app.modules.notifications.domain.entities import Notification, NotificationEvent


class NotificationSenderProtocol(Protocol):
    """Infrastructure port implemented by the FCM adapter (Band 11)."""

    async def send_push(
        self, *, device_token: str, title: str, body: str, data: dict[str, Any]
    ) -> None: ...


class NotificationServiceProtocol(Protocol):
    async def notify_user(
        self, user_id: uuid.UUID, *, event: NotificationEvent, title: str, body: str
    ) -> Notification: ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[Notification]: ...

    async def mark_read(self, notification_id: uuid.UUID) -> None: ...
