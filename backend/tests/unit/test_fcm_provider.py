"""Unit tests for FcmNotificationSender — no real Firebase app, no network.
Uses the `send_fn` test seam to stand in for `firebase_admin.messaging.send`.
"""

from __future__ import annotations

import pytest
from firebase_admin import exceptions, messaging

from app.core.config import Settings
from app.modules.notifications.infrastructure.fcm_provider import (
    FcmNotificationSender,
    InvalidDeviceTokenError,
    NotificationDeliveryError,
)


def test_missing_config_raises_without_app_or_send_fn() -> None:
    settings = Settings(fcm_project_id="", fcm_credentials_json_path="")
    with pytest.raises(NotificationDeliveryError, match="must both be set"):
        FcmNotificationSender(settings)


def test_neither_settings_app_nor_send_fn_raises() -> None:
    with pytest.raises(NotificationDeliveryError, match="one of"):
        FcmNotificationSender()


async def test_send_push_calls_send_fn_with_correct_message() -> None:
    captured: list[messaging.Message] = []

    def fake_send(message: messaging.Message) -> str:
        captured.append(message)
        return "projects/x/messages/1"

    sender = FcmNotificationSender(send_fn=fake_send)
    await sender.send_push(
        device_token="tok-123", title="Hallo", body="Welt", data={"offer_id": "abc", "score": 90}
    )

    assert len(captured) == 1
    message = captured[0]
    assert message.token == "tok-123"
    assert message.notification.title == "Hallo"
    assert message.notification.body == "Welt"
    assert message.data == {"offer_id": "abc", "score": "90"}  # FCM data must be str->str


async def test_send_push_raises_invalid_device_token_on_unregistered() -> None:
    def fake_send(message: messaging.Message) -> str:
        raise messaging.UnregisteredError("token gone")

    sender = FcmNotificationSender(send_fn=fake_send)
    with pytest.raises(InvalidDeviceTokenError):
        await sender.send_push(device_token="tok-123", title="t", body="b", data={})


async def test_send_push_raises_delivery_error_on_other_firebase_errors() -> None:
    def fake_send(message: messaging.Message) -> str:
        raise exceptions.UnavailableError("try again later")

    sender = FcmNotificationSender(send_fn=fake_send)
    with pytest.raises(NotificationDeliveryError):
        await sender.send_push(device_token="tok-123", title="t", body="b", data={})
