"""End-to-end HTTP tests for the auth + users API. Requires PostgreSQL (see conftest.py).

Runs against the real ASGI app but with the app's own global DB engine
pointed at the same database as `db_session` (both read `get_settings()`),
so requests exercise the actual FastAPI dependency graph, not a fake.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """`db_session` isn't used directly — depending on it ensures the schema
    exists before any request hits the app's own (separately connected) engine."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_register_login_me_refresh_logout_flow(client: AsyncClient) -> None:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "correcthorsebattery"},
    )
    assert register.status_code == 201
    user_id = register.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "correcthorsebattery"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"

    me = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["id"] == user_id
    assert me.json()["email"] == "flow@example.com"

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    logout = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert logout.status_code == 204

    reuse_after_logout = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert reuse_after_logout.status_code == 401


async def test_me_without_token_is_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "unauthorized"
    assert "correlation_id" in body


async def test_duplicate_registration_is_conflict(client: AsyncClient) -> None:
    payload = {"email": "dup-api@example.com", "password": "correcthorsebattery"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"
