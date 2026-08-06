"""Unit tests for IngestionService — the Band 07 pipeline orchestration,
tested against in-memory fakes for every port (no network, no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.modules.offers.application.ingestion import IngestionService
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource, RawListing


class FakeProvider:
    source = OfferSource.EBAY.value

    def __init__(self, listings: list[RawListing]) -> None:
        self._listings = listings

    async def search(
        self, *, category: OfferCategory, query: str | None = None, limit: int = 20
    ) -> list[RawListing]:
        return self._listings[:limit]


class FailingNormalizerOnce:
    """Normalizes everything except one poison listing, to prove one bad
    item doesn't abort the batch."""

    def __init__(self, poison_id: str) -> None:
        self._poison_id = poison_id

    def normalize(self, raw: RawListing) -> Offer:
        if raw.source_listing_id == self._poison_id:
            raise ValueError("boom")
        return Offer(
            id=uuid.uuid4(),
            source=raw.source,
            source_listing_id=raw.source_listing_id,
            title=raw.payload.get("title", "A valid title"),
            description="",
            price_amount=float(raw.payload.get("price_amount", 100)),
            price_currency="EUR",
            category=raw.category,
            url=f"https://example.com/{raw.source_listing_id}",
        )


class RejectEverythingValidator:
    def validate(self, offer: Offer) -> list[str]:
        return ["rejected for test purposes"]


class AcceptEverythingValidator:
    def validate(self, offer: Offer) -> list[str]:
        return []


class FakeOfferRepository:
    def __init__(self) -> None:
        self.persisted: list[Offer] = []

    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        return next((o for o in self.persisted if o.id == offer_id), None)

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool:
        return any(o.source_listing_id == source_listing_id for o in self.persisted)

    async def upsert(self, offer: Offer) -> Offer:
        self.persisted.append(offer)
        return offer

    async def list_by_category(
        self, category: str, *, page: int = 1, page_size: int = 20
    ) -> list[Offer]:
        matching = [o for o in self.persisted if o.category.value == category]
        offset = max(page - 1, 0) * page_size
        return matching[offset : offset + page_size]

    async def count_by_category(self, category: str) -> int:
        return len([o for o in self.persisted if o.category.value == category])


def _raw(listing_id: str, title: str = "A valid MacBook listing") -> RawListing:
    return RawListing(
        source=OfferSource.EBAY,
        source_listing_id=listing_id,
        category=OfferCategory.MACBOOK,
        payload={"title": title, "price_amount": 500},
    )


async def test_ingest_persists_all_valid_normalized_offers() -> None:
    provider = FakeProvider([_raw("1"), _raw("2"), _raw("3")])
    repo = FakeOfferRepository()
    service = IngestionService(
        provider, FailingNormalizerOnce("__none__"), AcceptEverythingValidator(), repo
    )

    result = await service.ingest(category=OfferCategory.MACBOOK)

    assert result.fetched == 3
    assert result.normalized == 3
    assert result.rejected == 0
    assert result.persisted == 3
    assert len(repo.persisted) == 3


async def test_ingest_skips_listing_that_fails_normalization_but_keeps_going() -> None:
    provider = FakeProvider([_raw("1"), _raw("poison"), _raw("3")])
    repo = FakeOfferRepository()
    service = IngestionService(
        provider, FailingNormalizerOnce("poison"), AcceptEverythingValidator(), repo
    )

    result = await service.ingest(category=OfferCategory.MACBOOK)

    assert result.fetched == 3
    assert result.normalized == 2  # "poison" failed to normalize
    assert result.persisted == 2
    assert any("poison" in e for e in result.errors)


async def test_ingest_rejects_offers_that_fail_validation() -> None:
    provider = FakeProvider([_raw("1"), _raw("2")])
    repo = FakeOfferRepository()
    service = IngestionService(
        provider, FailingNormalizerOnce("__none__"), RejectEverythingValidator(), repo
    )

    result = await service.ingest(category=OfferCategory.MACBOOK)

    assert result.normalized == 2
    assert result.rejected == 2
    assert result.persisted == 0
    assert repo.persisted == []


async def test_ingest_with_no_listings_returns_zeroed_result() -> None:
    provider = FakeProvider([])
    repo = FakeOfferRepository()
    service = IngestionService(
        provider, FailingNormalizerOnce("__none__"), AcceptEverythingValidator(), repo
    )

    result = await service.ingest(category=OfferCategory.MACBOOK)

    assert result.fetched == 0
    assert result.persisted == 0
    assert result.errors == []


@pytest.mark.parametrize("limit", [1, 2])
async def test_ingest_respects_limit_via_provider(limit: int) -> None:
    provider = FakeProvider([_raw("1"), _raw("2"), _raw("3")])
    repo = FakeOfferRepository()
    service = IngestionService(
        provider, FailingNormalizerOnce("__none__"), AcceptEverythingValidator(), repo
    )

    result = await service.ingest(category=OfferCategory.MACBOOK, limit=limit)

    assert result.fetched == limit


async def test_ingest_calls_on_offer_persisted_hook_for_each_persisted_offer() -> None:
    provider = FakeProvider([_raw("1"), _raw("2")])
    repo = FakeOfferRepository()
    persisted_offers: list[Offer] = []

    async def hook(offer: Offer) -> None:
        persisted_offers.append(offer)

    service = IngestionService(
        provider,
        FailingNormalizerOnce("__none__"),
        AcceptEverythingValidator(),
        repo,
        on_offer_persisted=hook,
    )

    result = await service.ingest(category=OfferCategory.MACBOOK)

    assert result.persisted == 2
    assert len(persisted_offers) == 2
    assert {o.source_listing_id for o in persisted_offers} == {"1", "2"}


async def test_ingest_survives_a_failing_hook() -> None:
    provider = FakeProvider([_raw("1")])
    repo = FakeOfferRepository()

    async def failing_hook(offer: Offer) -> None:
        raise RuntimeError("boom")

    service = IngestionService(
        provider,
        FailingNormalizerOnce("__none__"),
        AcceptEverythingValidator(),
        repo,
        on_offer_persisted=failing_hook,
    )

    # Must not raise — a hook failure must not lose the already-persisted offer.
    result = await service.ingest(category=OfferCategory.MACBOOK)

    assert result.persisted == 1
    assert len(repo.persisted) == 1
