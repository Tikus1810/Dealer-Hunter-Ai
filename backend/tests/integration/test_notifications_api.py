"""End-to-end HTTP tests for the Notifications API. Requires PostgreSQL
(see conftest.py). No FCM credentials are configured in tests, so device
registration/preferences/listing are exercised — actual push delivery
(FcmNotificationSender) is unit-tested separately in test_fcm_provider.py
against a fake send_fn, not here.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _auth_headers(client: AsyncClient, *, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correcthorsebattery"}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correcthorsebattery"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_register_and_unregister_device(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="notif-device@example.com")

    register = await client.post(
        "/api/v1/notifications/devices",
        headers=headers,
        json={"token": "device-token-abc", "platform": "android"},
    )
    assert register.status_code == 201
    assert register.json()["token"] == "device-token-abc"
    assert register.json()["is_active"] is True

    unregister = await client.request(
        "DELETE",
        "/api/v1/notifications/devices",
        headers=headers,
        json={"token": "device-token-abc"},
    )
    assert unregister.status_code == 204


async def test_devices_require_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/notifications/devices", json={"token": "x", "platform": "ios"}
    )
    assert response.status_code == 401


async def test_preferences_default_empty_then_can_be_set(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="notif-prefs@example.com")

    initial = await client.get("/api/v1/notifications/preferences", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == []

    set_response = await client.put(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={"event": "price_drop", "channel": "push", "enabled": False},
    )
    assert set_response.status_code == 200
    assert set_response.json()["enabled"] is False

    listed = await client.get("/api/v1/notifications/preferences", headers=headers)
    assert len(listed.json()) == 1
    assert listed.json()[0]["event"] == "price_drop"
    assert listed.json()[0]["enabled"] is False


async def test_list_notifications_empty_for_new_user(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="notif-empty@example.com")
    response = await client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_mark_unknown_notification_read_is_404(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="notif-404@example.com")
    response = await client.post(f"/api/v1/notifications/{uuid.uuid4()}/read", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_notifications_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/notifications")
    assert response.status_code == 401
