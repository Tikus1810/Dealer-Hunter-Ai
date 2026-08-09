"""Public interface of the `notifications` module (Band 11)."""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from app.modules.notifications.domain.entities import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
)


class NotificationSenderProtocol(Protocol):
    """Infrastructure port implemented by the FCM adapter (Band 11).

    Raises `InvalidDeviceTokenError` (app.modules.notifications.infrastructure.
    fcm_provider) when FCM reports the token as unregistered — the caller
    should deactivate it rather than retry. Raises the broader
    `NotificationDeliveryError` for transient failures, which the caller may
    retry (Band 11: delivery retries).
    """

    async def send_push(
        self, *, device_token: str, title: str, body: str, data: dict[str, Any]
    ) -> None: ...


class EmailSenderProtocol(Protocol):
    """Infrastructure port implemented by the Resend adapter (Band 11).

    A separate protocol from `NotificationSenderProtocol` (push) rather
    than one sender with two methods: each channel's provider adapter
    only implements what it actually can, and swapping one channel's
    provider (e.g. Resend for another email API later) never touches the
    other channel's interface.

    Raises `EmailDeliveryError` (app.modules.notifications.infrastructure.
    resend_provider) for any failure — the caller may retry (Band 11:
    delivery retries)."""

    async def send_email(self, *, to: str, subject: str, body: str) -> None: ...


class DeviceTokenRepositoryProtocol(Protocol):
    async def register(self, device_token: DeviceToken) -> DeviceToken:
        """Idempotent on `token`: registering an already-known token again
        just reassigns ownership and reactivates it (a device can change
        which account is logged in; a token should never belong to two
        users' active registrations at once)."""
        ...

    async def deactivate(self, user_id: uuid.UUID, token: str) -> None: ...

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[DeviceToken]: ...


class NotificationRepositoryProtocol(Protocol):
    async def save(self, notification: Notification) -> Notification: ...

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None: ...

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> list[Notification]: ...

    async def count_for_user(self, user_id: uuid.UUID) -> int: ...

    async def mark_read(self, notification_id: uuid.UUID) -> None: ...


class NotificationPreferenceRepositoryProtocol(Protocol):
    async def list_for_user(self, user_id: uuid.UUID) -> list[NotificationPreference]: ...

    async def upsert(self, preference: NotificationPreference) -> NotificationPreference: ...


class NotificationServiceProtocol(Protocol):
    async def register_device(
        self, user_id: uuid.UUID, *, token: str, platform: DevicePlatform
    ) -> DeviceToken: ...

    async def unregister_device(self, user_id: uuid.UUID, *, token: str) -> None: ...

    async def notify_user(
        self, user_id: uuid.UUID, *, event: NotificationEvent, data: dict[str, Any]
    ) -> list[Notification]:
        """Renders the event's template, checks the user's preference per
        channel, persists a `Notification` record per enabled channel
        (the audit log Band 11 asks for), and best-effort pushes to every
        active device via PUSH. A device whose token FCM reports as
        unregistered is deactivated automatically. Never raises for
        delivery failures — those are logged, not propagated, so one bad
        device token can't fail the whole call."""
        ...

    async def list_notifications(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Notification], int]: ...

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None: ...

    async def get_preferences(self, user_id: uuid.UUID) -> list[NotificationPreference]: ...

    async def set_preference(
        self,
        user_id: uuid.UUID,
        *,
        event: NotificationEvent,
        channel: NotificationChannel,
        enabled: bool,
    ) -> NotificationPreference: ...
