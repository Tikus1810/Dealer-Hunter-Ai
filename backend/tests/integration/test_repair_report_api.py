"""End-to-end HTTP test for the RepairBrain API. Requires PostgreSQL (see conftest.py).

Seeds via `app.db.session.session_factory` for the same reason as
`test_deal_score_api.py` — see that file's module docstring.
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_offer(*, description: str) -> Offer:
    async with session_factory() as session:
        # Idempotent — see test_deal_score_api.py's _seed_offer comment.
        existing = (
            await session.execute(
                select(CategoryModel).where(CategoryModel.code == OfferCategory.MACBOOK.value)
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(CategoryModel(code=OfferCategory.MACBOOK.value, name="MacBooks"))
            await session.flush()
        offer = await SqlAlchemyOfferRepository(session).upsert(
            Offer(
                id=uuid.uuid4(),
                source=OfferSource.EBAY,
                source_listing_id=f"repair-report-api-test-{uuid.uuid4()}",
                title="MacBook Air M1",
                description=description,
                price_amount=500.0,
                price_currency="EUR",
                category=OfferCategory.MACBOOK,
                url="https://ebay.de/itm/repair-report-api-test",
            )
        )
        await session.commit()
        return offer


async def test_create_repair_report_returns_full_report(client: AsyncClient) -> None:
    offer = await _seed_offer(description="Funktioniert einwandfrei.")

    response = await client.post(
        f"/api/v1/offers/{offer.id}/repair-report", json={"reported_defects": ["Akku defekt"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["offer_id"] == str(offer.id)
    assert 0 <= body["repair_score"] <= 100
    assert body["difficulty"] in {"beginner", "intermediate", "advanced"}
    assert body["compatible_parts"]
    assert body["summary"]


async def test_create_repair_report_for_unknown_offer_is_404(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/offers/{uuid.uuid4()}/repair-report", json={"reported_defects": []}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
