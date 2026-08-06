"""Unit tests for NotificationService against in-memory fakes — no DB, no
real FCM, no network.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core.exceptions import NotFoundError
from app.modules.notifications.application.service import NotificationService
from app.modules.notifications.domain.entities import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
)
from app.modules.notifications.infrastructure.fcm_provider import (
    InvalidDeviceTokenError,
    NotificationDeliveryError,
)


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.saved: dict[uuid.UUID, Notification] = {}

    async def save(self, notification: Notification) -> Notification:
        self.saved[notification.id] = notification
        return notification

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        return self.saved.get(notification_id)

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> list[Notification]:
        matching = [n for n in self.saved.values() if n.user_id == user_id]
        offset = max(page - 1, 0) * page_size
        return matching[offset : offset + page_size]

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        return len([n for n in self.saved.values() if n.user_id == user_id])

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        self.saved[notification_id].is_read = True


class FakeDeviceTokenRepository:
    def __init__(self, devices: list[DeviceToken] | None = None) -> None:
        self._devices = {d.token: d for d in (devices or [])}

    async def register(self, device_token: DeviceToken) -> DeviceToken:
        self._devices[device_token.token] = device_token
        return device_token

    async def deactivate(self, user_id: uuid.UUID, token: str) -> None:
        if token in self._devices:
            self._devices[token].is_active = False

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[DeviceToken]:
        return [d for d in self._devices.values() if d.user_id == user_id and d.is_active]


class FakePreferenceRepository:
    def __init__(self, preferences: list[NotificationPreference] | None = None) -> None:
        self._preferences = list(preferences or [])

    async def list_for_user(self, user_id: uuid.UUID) -> list[NotificationPreference]:
        return [p for p in self._preferences if p.user_id == user_id]

    async def upsert(self, preference: NotificationPreference) -> NotificationPreference:
        self._preferences = [
            p
            for p in self._preferences
            if not (
                p.user_id == preference.user_id
                and p.event == preference.event
                and p.channel == preference.channel
            )
        ]
        self._preferences.append(preference)
        return preference


class FakeSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_with: Exception | None = None

    async def send_push(
        self, *, device_token: str, title: str, body: str, data: dict[str, Any]
    ) -> None:
        self.calls.append({"device_token": device_token, "title": title, "body": body})
        if self.fail_with is not None:
            raise self.fail_with


async def test_notify_user_persists_notification_for_default_enabled_channels() -> None:
    user_id = uuid.uuid4()
    service = NotificationService(
        FakeNotificationRepository(), FakeDeviceTokenRepository(), FakePreferenceRepository()
    )

    created = await service.notify_user(
        user_id, event=NotificationEvent.SAVED_SEARCH_MATCH, data={"offer_title": "MacBook"}
    )

    channels = {n.channel for n in created}
    assert channels == {NotificationChannel.PUSH, NotificationChannel.EMAIL}
    assert all(n.user_id == user_id for n in created)
    assert all("MacBook" in n.body for n in created)


async def test_notify_user_skips_disabled_channel() -> None:
    user_id = uuid.uuid4()
    prefs = FakePreferenceRepository(
        [
            NotificationPreference(
                user_id=user_id,
                event=NotificationEvent.SAVED_SEARCH_MATCH,
                channel=NotificationChannel.EMAIL,
                enabled=False,
            )
        ]
    )
    service = NotificationService(FakeNotificationRepository(), FakeDeviceTokenRepository(), prefs)

    created = await service.notify_user(
        user_id, event=NotificationEvent.SAVED_SEARCH_MATCH, data={}
    )

    assert {n.channel for n in created} == {NotificationChannel.PUSH}


async def test_notify_user_pushes_to_every_active_device() -> None:
    user_id = uuid.uuid4()
    devices = [
        DeviceToken(id=uuid.uuid4(), user_id=user_id, token="tok-a", platform=DevicePlatform.IOS),
        DeviceToken(
            id=uuid.uuid4(), user_id=user_id, token="tok-b", platform=DevicePlatform.ANDROID
        ),
    ]
    sender = FakeSender()
    service = NotificationService(
        FakeNotificationRepository(),
        FakeDeviceTokenRepository(devices),
        FakePreferenceRepository(),
        sender=sender,
    )

    await service.notify_user(user_id, event=NotificationEvent.SAVED_SEARCH_MATCH, data={})

    assert {c["device_token"] for c in sender.calls} == {"tok-a", "tok-b"}


async def test_notify_user_without_sender_configured_still_persists() -> None:
    user_id = uuid.uuid4()
    service = NotificationService(
        FakeNotificationRepository(), FakeDeviceTokenRepository(), FakePreferenceRepository()
    )
    created = await service.notify_user(
        user_id, event=NotificationEvent.SAVED_SEARCH_MATCH, data={}
    )
    assert len(created) == 2  # PUSH + EMAIL records still created, just not delivered


async def test_notify_user_deactivates_device_on_invalid_token() -> None:
    user_id = uuid.uuid4()
    device = DeviceToken(
        id=uuid.uuid4(), user_id=user_id, token="dead-tok", platform=DevicePlatform.IOS
    )
    device_repo = FakeDeviceTokenRepository([device])
    sender = FakeSender()
    sender.fail_with = InvalidDeviceTokenError("gone")
    service = NotificationService(
        FakeNotificationRepository(), device_repo, FakePreferenceRepository(), sender=sender
    )

    await service.notify_user(user_id, event=NotificationEvent.SAVED_SEARCH_MATCH, data={})

    assert await device_repo.list_active_for_user(user_id) == []


async def test_notify_user_does_not_raise_on_transient_delivery_failure() -> None:
    user_id = uuid.uuid4()
    device = DeviceToken(id=uuid.uuid4(), user_id=user_id, token="tok", platform=DevicePlatform.IOS)
    sender = FakeSender()
    sender.fail_with = NotificationDeliveryError("temporary outage")
    service = NotificationService(
        FakeNotificationRepository(),
        FakeDeviceTokenRepository([device]),
        FakePreferenceRepository(),
        sender=sender,
    )

    # Must not raise.
    created = await service.notify_user(
        user_id, event=NotificationEvent.SAVED_SEARCH_MATCH, data={}
    )
    assert len(created) == 2


async def test_list_notifications_returns_page_and_total() -> None:
    user_id = uuid.uuid4()
    repo = FakeNotificationRepository()
    service = NotificationService(repo, FakeDeviceTokenRepository(), FakePreferenceRepository())
    for _ in range(3):
        await service.notify_user(user_id, event=NotificationEvent.DEAL_SCORE_READY, data={})

    notifications, total = await service.list_notifications(user_id, page=1, page_size=100)

    assert total == 6  # 3 events x 2 channels each
    assert len(notifications) == 6


async def test_mark_read_updates_the_notification() -> None:
    user_id = uuid.uuid4()
    repo = FakeNotificationRepository()
    service = NotificationService(repo, FakeDeviceTokenRepository(), FakePreferenceRepository())
    created = await service.notify_user(
        user_id, event=NotificationEvent.DEAL_SCORE_READY, data={}
    )

    await service.mark_read(user_id, created[0].id)

    assert repo.saved[created[0].id].is_read is True


async def test_mark_read_raises_not_found_for_other_users_notification() -> None:
    owner, intruder = uuid.uuid4(), uuid.uuid4()
    repo = FakeNotificationRepository()
    service = NotificationService(repo, FakeDeviceTokenRepository(), FakePreferenceRepository())
    created = await service.notify_user(owner, event=NotificationEvent.DEAL_SCORE_READY, data={})

    with pytest.raises(NotFoundError):
        await service.mark_read(intruder, created[0].id)


async def test_set_preference_then_get_preferences_reflects_it() -> None:
    user_id = uuid.uuid4()
    service = NotificationService(
        FakeNotificationRepository(), FakeDeviceTokenRepository(), FakePreferenceRepository()
    )

    await service.set_preference(
        user_id,
        event=NotificationEvent.PRICE_DROP,
        channel=NotificationChannel.PUSH,
        enabled=False,
    )
    preferences = await service.get_preferences(user_id)

    assert len(preferences) == 1
    assert preferences[0].enabled is False


async def test_register_and_unregister_device() -> None:
    user_id = uuid.uuid4()
    device_repo = FakeDeviceTokenRepository()
    service = NotificationService(
        FakeNotificationRepository(), device_repo, FakePreferenceRepository()
    )

    await service.register_device(user_id, token="tok-1", platform=DevicePlatform.WEB)
    assert len(await device_repo.list_active_for_user(user_id)) == 1

    await service.unregister_device(user_id, token="tok-1")
    assert await device_repo.list_active_for_user(user_id) == []
