"""Firebase Cloud Messaging adapter — implements `NotificationSenderProtocol`
(Band 11). Optional, same pattern as the eBay official API and Claude Vision
providers: without `FCM_PROJECT_ID`/`FCM_CREDENTIALS_JSON_PATH` configured,
this raises a clear error at construction time rather than being wired in
at all — see `presentation/router.py`'s `get_notification_service` for the
"only construct if configured" gate.

`firebase_admin.messaging.send()` is a synchronous, blocking network call
(the SDK has no native asyncio support) — wrapped in `asyncio.to_thread` so
it doesn't block the event loop, consistent with this codebase's fully
async architecture elsewhere.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any

import firebase_admin
from firebase_admin import credentials, exceptions, messaging

from app.core.config import Settings

_FCM_APP_NAME = "dealhunter-fcm"


class NotificationDeliveryError(Exception):
    """FCM rejected or failed to deliver a push (network error, quota,
    malformed message, ...). The caller may retry (Band 11: delivery
    retries) — this is not necessarily the device token's fault."""


class InvalidDeviceTokenError(NotificationDeliveryError):
    """FCM reports this token as unregistered/invalid. Retrying won't help —
    the caller should deactivate the token instead."""


def _get_or_create_app(settings: Settings) -> firebase_admin.App:
    """Reuses one named Firebase app per process. `initialize_app` isn't
    idempotent (a second call with the same name raises `ValueError`), and
    this is constructed fresh per request by the router's DI (see
    `get_notification_service`), so a naive re-init would blow up after the
    first request."""
    try:
        return firebase_admin.get_app(_FCM_APP_NAME)
    except ValueError:
        cred = credentials.Certificate(settings.fcm_credentials_json_path)
        return firebase_admin.initialize_app(
            cred, {"projectId": settings.fcm_project_id}, name=_FCM_APP_NAME
        )


class FcmNotificationSender:
    """Implements `NotificationSenderProtocol`
    (app.modules.notifications.application.interfaces)."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        app: firebase_admin.App | None = None,
        send_fn: Callable[[messaging.Message], str] | None = None,
    ) -> None:
        """`send_fn` is a test seam (mirrors `ClaudeCosmeticConditionAnalyzer`'s
        `client` param): pass a fake to unit-test `send_push`'s error mapping
        without a real Firebase app or network. Production code should pass
        `settings` (or a pre-built `app`) and let this resolve the real
        `messaging.send`."""
        if send_fn is not None:
            self._send_fn = send_fn
        elif app is not None:
            self._send_fn = functools.partial(messaging.send, app=app)
        elif settings is not None:
            if not settings.fcm_project_id or not settings.fcm_credentials_json_path:
                raise NotificationDeliveryError(
                    "FCM_PROJECT_ID and FCM_CREDENTIALS_JSON_PATH must both be set"
                )
            self._send_fn = functools.partial(messaging.send, app=_get_or_create_app(settings))
        else:
            raise NotificationDeliveryError("one of settings, app, or send_fn must be provided")

    async def send_push(
        self, *, device_token: str, title: str, body: str, data: dict[str, Any]
    ) -> None:
        # `token=` (not the newer `fid=`) deliberately: firebase-admin 7.x
        # deprecated Message.token with a DeprecationWarning (visible in the
        # test suite's warnings summary) in favor of `fid`, but this hasn't
        # been verified against a live Firebase project yet (see the README's
        # "known gaps" — FCM_PROJECT_ID isn't configured anywhere real), and
        # `fid` (Firebase Installation ID) may not be a drop-in-equivalent
        # concept for an FCM registration token. Switch once verified against
        # a real send, not on a guess.
        message = messaging.Message(
            token=device_token,
            notification=messaging.Notification(title=title, body=body),
            # FCM's data payload must be string-to-string.
            data={key: str(value) for key, value in data.items()},
        )
        try:
            await asyncio.to_thread(self._send_fn, message)
        except messaging.UnregisteredError as exc:
            raise InvalidDeviceTokenError(f"device token is no longer registered: {exc}") from exc
        except exceptions.FirebaseError as exc:
            raise NotificationDeliveryError(f"FCM send failed: {exc}") from exc
