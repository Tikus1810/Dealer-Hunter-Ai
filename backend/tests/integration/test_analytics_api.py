"""End-to-end HTTP tests for the Analytics API. Requires PostgreSQL (see
conftest.py)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_factory
from app.main import app
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.offers.infrastructure.models import CategoryModel
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository

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


async def test_track_event_then_appears_in_recent_and_summary(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="analytics-track@example.com")

    tracked = await client.post(
        "/api/v1/analytics/events",
        headers=headers,
        json={"event_name": "screen_view", "properties": {"screen": "offer_list"}},
    )
    assert tracked.status_code == 201

    recent = await client.get("/api/v1/analytics/events/screen_view", headers=headers)
    assert recent.status_code == 200
    events = recent.json()
    assert any(e["properties"].get("screen") == "offer_list" for e in events)

    summary = await client.get(
        "/api/v1/analytics/summary", headers=headers, params={"event_name": "screen_view"}
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["event_name"] == "screen_view"
    assert body["count"] >= 1


async def test_track_event_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/analytics/events", json={"event_name": "screen_view", "properties": {}}
    )
    assert response.status_code == 401


async def test_track_event_rejects_a_denylisted_property_key(client: AsyncClient) -> None:
    headers = await _auth_headers(client, email="analytics-denylist@example.com")

    response = await client.post(
        "/api/v1/analytics/events",
        headers=headers,
        json={"event_name": "screen_view", "properties": {"email": "leak@example.com"}},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_registering_a_user_automatically_tracks_user_registered(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client, email="analytics-auto@example.com")

    summary = await client.get(
        "/api/v1/analytics/summary", headers=headers, params={"event_name": "user_registered"}
    )

    assert summary.status_code == 200
    assert summary.json()["count"] >= 1


async def _seed_offer() -> Offer:
    # Seeds through the app's own `session_factory` engine (not the
    # `db_session` fixture's isolated, rolled-back transaction), same
    # pattern as test_offers_api.py — the HTTP client below hits the real
    # app, which reads through that same real engine.
    async with session_factory() as session:
        existing = (
            await session.execute(
                select(CategoryModel).where(CategoryModel.code == OfferCategory.MACBOOK)
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(CategoryModel(code=OfferCategory.MACBOOK, name="MacBooks"))
            await session.flush()
        offer = await SqlAlchemyOfferRepository(session).upsert(
            Offer(
                id=uuid.uuid4(),
                source=OfferSource.EBAY,
                source_listing_id=f"analytics-api-test-{uuid.uuid4()}",
                title="MacBook Air M2",
                description="",
                price_amount=700.0,
                price_currency="EUR",
                category=OfferCategory.MACBOOK,
                url="https://example.com/x",
            )
        )
        await session.commit()
        return offer


async def test_favoriting_an_offer_automatically_tracks_offer_favorited(
    client: AsyncClient,
) -> None:
    offer = await _seed_offer()
    headers = await _auth_headers(client, email="analytics-favorite@example.com")

    favorited = await client.post(f"/api/v1/offers/{offer.id}/favorite", headers=headers)
    assert favorited.status_code == 201

    summary = await client.get(
        "/api/v1/analytics/summary", headers=headers, params={"event_name": "offer_favorited"}
    )
    assert summary.status_code == 200
    assert summary.json()["count"] >= 1
