"""End-to-end HTTP tests for the Offers + Favorites API. Requires PostgreSQL
(see conftest.py). Same pattern as test_deal_score_api.py: seeds through the
app's own `session_factory` engine, then drives everything over real HTTP.
"""

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
    """`db_session` isn't used directly — depending on it ensures the schema
    exists (via the shared `_schema` fixture) before any request runs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_offer(*, price: float = 900.0, category_code: str = OfferCategory.MACBOOK) -> Offer:
    async with session_factory() as session:
        existing = (
            await session.execute(select(CategoryModel).where(CategoryModel.code == category_code))
        ).scalar_one_or_none()
        if existing is None:
            session.add(CategoryModel(code=category_code, name=category_code))
            await session.flush()
        offer = await SqlAlchemyOfferRepository(session).upsert(
            Offer(
                id=uuid.uuid4(),
                source=OfferSource.EBAY,
                source_listing_id=f"offers-api-test-{uuid.uuid4()}",
                title="MacBook Air M1, wie neu, OVP",
                description="Kaum benutzt, alles dabei.",
                price_amount=price,
                price_currency="EUR",
                category=OfferCategory(category_code),
                images=["a.jpg", "b.jpg"],
                location="Hamburg",
                url="https://ebay.de/itm/offers-api-test",
            )
        )
        await session.commit()
        return offer


async def _register_and_login(client: AsyncClient, *, email: str) -> str:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correcthorsebattery"}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correcthorsebattery"}
    )
    token: str = login.json()["access_token"]
    return token


async def test_list_offers_returns_only_matching_category(client: AsyncClient) -> None:
    macbook = await _seed_offer(category_code=OfferCategory.MACBOOK)
    iphone = await _seed_offer(category_code=OfferCategory.IPHONE)

    response = await client.get("/api/v1/offers", params={"category": "macbook"})

    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert str(macbook.id) in ids
    assert str(iphone.id) not in ids
    assert body["page"] == 1
    assert body["page_size"] == 20


async def test_list_offers_requires_category(client: AsyncClient) -> None:
    response = await client.get("/api/v1/offers")
    assert response.status_code == 422


async def test_get_offer_returns_detail(client: AsyncClient) -> None:
    offer = await _seed_offer()

    response = await client.get(f"/api/v1/offers/{offer.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(offer.id)


async def test_get_offer_for_unknown_id_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/offers/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_favorite_flow_add_list_remove(client: AsyncClient) -> None:
    offer = await _seed_offer()
    token = await _register_and_login(client, email="favorites-flow@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    add = await client.post(f"/api/v1/offers/{offer.id}/favorite", headers=headers)
    assert add.status_code == 201
    assert add.json()["offer_id"] == str(offer.id)

    listed = await client.get("/api/v1/favorites", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["offer_id"] == str(offer.id)

    remove = await client.delete(f"/api/v1/offers/{offer.id}/favorite", headers=headers)
    assert remove.status_code == 204

    listed_again = await client.get("/api/v1/favorites", headers=headers)
    assert listed_again.json()["total"] == 0


async def test_add_favorite_twice_is_conflict(client: AsyncClient) -> None:
    offer = await _seed_offer()
    token = await _register_and_login(client, email="favorites-conflict@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post(f"/api/v1/offers/{offer.id}/favorite", headers=headers)
    assert first.status_code == 201

    second = await client.post(f"/api/v1/offers/{offer.id}/favorite", headers=headers)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_add_favorite_without_auth_is_unauthorized(client: AsyncClient) -> None:
    offer = await _seed_offer()
    response = await client.post(f"/api/v1/offers/{offer.id}/favorite")
    assert response.status_code == 401
