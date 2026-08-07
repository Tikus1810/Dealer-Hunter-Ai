"""End-to-end HTTP test for the DealBrain API. Requires PostgreSQL (see conftest.py).

Seeds data through `app.db.session.session_factory` — the same engine the
running `app` uses — rather than the rollback-wrapped `db_session` fixture,
because a rolled-back transaction on a *different* connection would never
be visible to the app's own request-handling connection anyway.
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


async def _seed_offer(*, price: float, category_code: str) -> Offer:
    async with session_factory() as session:
        # Idempotent — other integration test files commit a category with
        # this same code through this same real engine; a bare INSERT here
        # races a UniqueViolationError against whichever test ran first.
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
                source_listing_id=f"deal-score-api-test-{uuid.uuid4()}",
                title="MacBook Air M1, wie neu, OVP",
                description="Kaum benutzt, alles dabei.",
                price_amount=price,
                price_currency="EUR",
                category=OfferCategory.MACBOOK,
                images=["a.jpg", "b.jpg"],
                location="Hamburg",
                url="https://ebay.de/itm/deal-score-api-test",
            )
        )
        await session.commit()
        return offer


async def test_get_deal_score_computes_and_returns_a_score(client: AsyncClient) -> None:
    offer = await _seed_offer(price=650.0, category_code=OfferCategory.MACBOOK.value)

    response = await client.get(f"/api/v1/offers/{offer.id}/deal-score")

    assert response.status_code == 200
    body = response.json()
    assert body["offer_id"] == str(offer.id)
    assert 0 <= body["score"] <= 100
    assert body["recommendation"]
    assert body["scoring_version"] == "1.0.0"
    assert isinstance(body["explanation"], list)
    assert len(body["explanation"]) > 0


async def test_get_deal_score_for_unknown_offer_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/offers/{uuid.uuid4()}/deal-score")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
