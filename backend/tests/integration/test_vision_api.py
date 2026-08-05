"""End-to-end HTTP test for the Vision AI API. Requires PostgreSQL (see
conftest.py); the listing image itself is respx-mocked, not fetched for real.

Seeds via `app.db.session.session_factory` for the same reason as
`test_deal_score_api.py` — see that file's module docstring.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_factory
from app.main import app
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.offers.infrastructure.models import CategoryModel
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository

pytestmark = pytest.mark.integration

IMAGE_URL = "https://images.example.com/vision-api-test.jpg"


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_offer(*, images: list[str]) -> Offer:
    async with session_factory() as session:
        session.add(CategoryModel(code=OfferCategory.MACBOOK.value, name="MacBooks"))
        await session.flush()
        offer = await SqlAlchemyOfferRepository(session).upsert(
            Offer(
                id=uuid.uuid4(),
                source=OfferSource.EBAY,
                source_listing_id=f"vision-api-test-{uuid.uuid4()}",
                title="MacBook Air M1",
                description="Guter Zustand.",
                price_amount=650.0,
                price_currency="EUR",
                category=OfferCategory.MACBOOK,
                images=images,
                url="https://ebay.de/itm/vision-api-test",
            )
        )
        await session.commit()
        return offer


@respx.mock
async def test_get_vision_observation_returns_structured_observations(
    client: AsyncClient,
) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), color=(200, 200, 200)).save(buffer, format="PNG")
    respx.get(IMAGE_URL).mock(return_value=httpx.Response(200, content=buffer.getvalue()))

    offer = await _seed_offer(images=[IMAGE_URL])

    response = await client.get(f"/api/v1/offers/{offer.id}/vision-observation")

    assert response.status_code == 200
    body = response.json()
    assert body["offer_id"] == str(offer.id)
    assert body["image_count"] == 1
    assert body["is_image_set_incomplete"] is True  # 1 < MIN_IMAGES_FOR_COMPLETE_SET
    assert body["cosmetic_condition"] == "not_available"
    assert len(body["per_image"]) == 1
    assert body["per_image"][0]["is_reachable"] is True


async def test_get_vision_observation_for_unknown_offer_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/offers/{uuid.uuid4()}/vision-observation")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
