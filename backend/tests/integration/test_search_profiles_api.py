"""End-to-end HTTP tests for the Search Profiles API. Requires PostgreSQL
(see conftest.py).
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


async def test_search_profile_crud_flow(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="search-crud@example.com")

    create = await client.post(
        "/api/v1/search-profiles",
        headers=headers,
        json={"name": "Cheap MacBooks", "category": "macbook", "max_price": 800.0},
    )
    assert create.status_code == 201
    profile = create.json()
    assert profile["name"] == "Cheap MacBooks"
    assert profile["max_price"] == 800.0
    assert profile["is_active"] is True

    listed = await client.get("/api/v1/search-profiles", headers=headers)
    assert listed.status_code == 200
    assert any(p["id"] == profile["id"] for p in listed.json())

    fetched = await client.get(f"/api/v1/search-profiles/{profile['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == profile["id"]

    updated = await client.patch(
        f"/api/v1/search-profiles/{profile['id']}", headers=headers, json={"max_price": 900.0}
    )
    assert updated.status_code == 200
    assert updated.json()["max_price"] == 900.0
    assert updated.json()["name"] == "Cheap MacBooks"  # untouched by the partial update

    deleted = await client.delete(f"/api/v1/search-profiles/{profile['id']}", headers=headers)
    assert deleted.status_code == 204

    after_delete = await client.get(f"/api/v1/search-profiles/{profile['id']}", headers=headers)
    assert after_delete.status_code == 404


async def test_search_profile_is_not_visible_to_other_users(client: AsyncClient) -> None:
    owner_headers = await _auth_headers(client, email="search-owner@example.com")
    other_headers = await _auth_headers(client, email="search-intruder@example.com")

    create = await client.post(
        "/api/v1/search-profiles",
        headers=owner_headers,
        json={"name": "Owner's profile", "category": "macbook"},
    )
    profile_id = create.json()["id"]

    response = await client.get(f"/api/v1/search-profiles/{profile_id}", headers=other_headers)

    assert response.status_code == 404


async def test_search_profiles_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search-profiles")
    assert response.status_code == 401


async def test_get_unknown_search_profile_is_404(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="search-404@example.com")
    response = await client.get(f"/api/v1/search-profiles/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
