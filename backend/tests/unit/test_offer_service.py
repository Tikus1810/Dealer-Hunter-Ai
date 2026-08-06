"""Unit tests for OfferService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import NotFoundError
from app.modules.offers.application.service import OfferService
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource


class FakeOfferRepository:
    def __init__(self, offers: list[Offer]) -> None:
        self._offers = {o.id: o for o in offers}

    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        return self._offers.get(offer_id)

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool:
        raise NotImplementedError

    async def upsert(self, offer: Offer) -> Offer:
        raise NotImplementedError

    async def list_by_category(
        self, category: str, *, page: int = 1, page_size: int = 20
    ) -> list[Offer]:
        matching = [o for o in self._offers.values() if o.category.value == category]
        offset = max(page - 1, 0) * page_size
        return matching[offset : offset + page_size]

    async def count_by_category(self, category: str) -> int:
        return len([o for o in self._offers.values() if o.category.value == category])


def _offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": str(uuid.uuid4()),
        "title": "MacBook Pro 14 M3",
        "description": "Wie neu.",
        "price_amount": 900.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "url": "https://ebay.de/itm/x",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


async def test_get_offer_returns_the_offer() -> None:
    offer = _offer()
    service = OfferService(FakeOfferRepository([offer]))

    result = await service.get_offer(offer.id)

    assert result.id == offer.id


async def test_get_offer_raises_not_found_for_unknown_offer() -> None:
    service = OfferService(FakeOfferRepository([]))
    with pytest.raises(NotFoundError):
        await service.get_offer(uuid.uuid4())


async def test_list_offers_returns_page_and_total_count() -> None:
    offers = [_offer() for _ in range(5)]
    service = OfferService(FakeOfferRepository(offers))

    page, total = await service.list_offers(category="macbook", page=1, page_size=2)

    assert len(page) == 2
    assert total == 5


async def test_list_offers_filters_by_category() -> None:
    macbooks = [_offer(category=OfferCategory.MACBOOK) for _ in range(2)]
    iphones = [_offer(category=OfferCategory.IPHONE) for _ in range(3)]
    service = OfferService(FakeOfferRepository([*macbooks, *iphones]))

    page, total = await service.list_offers(category="iphone")

    assert total == 3
    assert all(o.category == OfferCategory.IPHONE for o in page)
