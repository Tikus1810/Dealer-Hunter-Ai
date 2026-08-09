"""Notifications application service — implements `NotificationServiceProtocol`
(Band 11).

Orchestrates: render template -> check preference per channel -> persist
(the audit log) -> best-effort push fan-out to every active device token.
Delivery failures are logged, never raised — Band 11's "delivery retries"
and "error handling" requirements mean one bad device token, FCM being
unreachable, or Resend being unreachable, must never fail the caller
(e.g. a search-profile match notification firing from inside the
ingestion pipeline — see `match_notifier.py`). PUSH and EMAIL are both
delivered when configured (`sender`/`email_sender` respectively) — an
EMAIL-channel notification is always recorded (the "audit log"
requirement) regardless of whether delivery is configured.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.modules.notifications.application.interfaces import (
    DeviceTokenRepositoryProtocol,
    EmailSenderProtocol,
    NotificationPreferenceRepositoryProtocol,
    NotificationRepositoryProtocol,
    NotificationSenderProtocol,
)
from app.modules.notifications.domain.entities import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
)
from app.modules.notifications.domain.preferences import PreferenceResolver
from app.modules.notifications.domain.templates import NotificationTemplateRenderer
from app.modules.notifications.infrastructure.fcm_provider import (
    InvalidDeviceTokenError,
    NotificationDeliveryError,
)
from app.modules.notifications.infrastructure.resend_provider import EmailDeliveryError
from app.modules.users.application.interfaces import UserRepositoryProtocol

logger = get_logger(__name__)


class NotificationService:
    def __init__(
        self,
        notifications: NotificationRepositoryProtocol,
        device_tokens: DeviceTokenRepositoryProtocol,
        preferences: NotificationPreferenceRepositoryProtocol,
        *,
        sender: NotificationSenderProtocol | None = None,
        email_sender: EmailSenderProtocol | None = None,
        users: UserRepositoryProtocol | None = None,
        template_renderer: NotificationTemplateRenderer | None = None,
        preference_resolver: PreferenceResolver | None = None,
    ) -> None:
        self._notifications = notifications
        self._device_tokens = device_tokens
        self._preferences = preferences
        self._sender = sender
        self._email_sender = email_sender
        # Only needed to resolve a user id to an email address for EMAIL
        # delivery — every existing call site keeps working unchanged
        # since this defaults to None (same optional-collaborator pattern
        # as `analytics` elsewhere in this codebase).
        self._users = users
        self._templates = template_renderer or NotificationTemplateRenderer()
        self._resolver = preference_resolver or PreferenceResolver()

    async def register_device(
        self, user_id: uuid.UUID, *, token: str, platform: DevicePlatform
    ) -> DeviceToken:
        device_token = DeviceToken(id=uuid.uuid4(), user_id=user_id, token=token, platform=platform)
        return await self._device_tokens.register(device_token)

    async def unregister_device(self, user_id: uuid.UUID, *, token: str) -> None:
        await self._device_tokens.deactivate(user_id, token)

    async def notify_user(
        self, user_id: uuid.UUID, *, event: NotificationEvent, data: dict[str, Any]
    ) -> list[Notification]:
        rendered = self._templates.render(event, data)
        user_preferences = await self._preferences.list_for_user(user_id)

        created: list[Notification] = []
        for channel in NotificationChannel:
            if not self._resolver.is_enabled(user_preferences, event=event, channel=channel):
                continue

            notification = Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                event=event,
                channel=channel,
                title=rendered.title,
                body=rendered.body,
                data=data or None,
            )
            saved = await self._notifications.save(notification)
            created.append(saved)

            if channel == NotificationChannel.PUSH:
                await self._deliver_push(
                    user_id, title=rendered.title, body=rendered.body, data=data
                )
            elif channel == NotificationChannel.EMAIL:
                await self._deliver_email(user_id, title=rendered.title, body=rendered.body)

        return created

    async def _deliver_push(
        self, user_id: uuid.UUID, *, title: str, body: str, data: dict[str, Any]
    ) -> None:
        if self._sender is None:
            return  # FCM not configured — see get_notification_service's gate
        devices = await self._device_tokens.list_active_for_user(user_id)
        for device in devices:
            try:
                await self._sender.send_push(
                    device_token=device.token, title=title, body=body, data=data
                )
            except InvalidDeviceTokenError:
                await self._device_tokens.deactivate(user_id, device.token)
            except NotificationDeliveryError as exc:
                logger.error(
                    "push_delivery_failed",
                    user_id=str(user_id),
                    device_id=str(device.id),
                    error=str(exc),
                )

    async def _deliver_email(self, user_id: uuid.UUID, *, title: str, body: str) -> None:
        if self._email_sender is None or self._users is None:
            return  # Resend not configured — see get_notification_service's gate
        user = await self._users.get_by_id(user_id)
        if user is None or not user.email:
            return
        try:
            await self._email_sender.send_email(to=user.email, subject=title, body=body)
        except EmailDeliveryError as exc:
            logger.error("email_delivery_failed", user_id=str(user_id), error=str(exc))

    async def list_notifications(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Notification], int]:
        notifications = await self._notifications.list_for_user(
            user_id, page=page, page_size=page_size
        )
        total = await self._notifications.count_for_user(user_id)
        return notifications, total

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        notification = await self._notifications.get_by_id(notification_id)
        if notification is None or notification.user_id != user_id:
            raise NotFoundError(
                "notification not found", details={"notification_id": str(notification_id)}
            )
        await self._notifications.mark_read(notification_id)

    async def get_preferences(self, user_id: uuid.UUID) -> list[NotificationPreference]:
        return await self._preferences.list_for_user(user_id)

    async def set_preference(
        self,
        user_id: uuid.UUID,
        *,
        event: NotificationEvent,
        channel: NotificationChannel,
        enabled: bool,
    ) -> NotificationPreference:
        preference = NotificationPreference(
            user_id=user_id, event=event, channel=channel, enabled=enabled
        )
        return await self._preferences.upsert(preference)
