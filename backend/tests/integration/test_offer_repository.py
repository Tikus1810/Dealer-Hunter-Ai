"""Integration tests for SqlAlchemyOfferRepository. Requires PostgreSQL (see conftest.py)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.offers.infrastructure.models import CategoryModel
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository

pytestmark = pytest.mark.integration


def _make_offer(
    *,
    source_listing_id: str = "12345",
    price: float = 899.0,
    category: OfferCategory = OfferCategory.MACBOOK,
) -> Offer:
    return Offer(
        id=uuid.uuid4(),
        source=OfferSource.EBAY,
        source_listing_id=source_listing_id,
        title="MacBook Pro 14 M3, wie neu",
        description="Kaum benutzt, keine Kratzer.",
        price_amount=price,
        price_currency="EUR",
        category=category,
        url="https://ebay.de/itm/12345",
    )


async def test_upsert_without_seeded_category_raises(db_session: AsyncSession) -> None:
    repo = SqlAlchemyOfferRepository(db_session)
    # GAME_CONSOLE specifically: every other integration test file that
    # seeds a category uses MACBOOK or IPHONE (grep confirms, as of this
    # writing) and commits it for real through the shared global engine —
    # this test needs a category code guaranteed absent from the whole
    # shared CI Postgres instance, not just this test's own (rolled-back)
    # transaction, since `_category_id_for`'s SELECT sees other sessions'
    # already-committed rows too. Fragile-by-convention, not by
    # construction: if a future test starts seeding GAME_CONSOLE, this
    # breaks the same way it just did for MACBOOK. No fully robust fix
    # exists without either deleting other tests' committed rows (risks a
    # real ForeignKeyViolation against their offers) or mocking the
    # category lookup directly instead of testing the real repository.
    with pytest.raises(NotFoundError):
        await repo.upsert(_make_offer(category=OfferCategory.GAME_CONSOLE))


async def test_upsert_creates_then_updates_on_same_source_listing(
    db_session: AsyncSession, seeded_category: CategoryModel
) -> None:
    repo = SqlAlchemyOfferRepository(db_session)

    created = await repo.upsert(_make_offer(price=899.0))
    assert created.price_amount == 899.0
    assert await repo.exists_by_source("ebay", "12345") is True

    updated = await repo.upsert(_make_offer(price=849.0))
    assert updated.id == created.id  # same listing => same row, not a duplicate
    assert updated.price_amount == 849.0


async def test_list_by_category_returns_only_matching_active_offers(
    db_session: AsyncSession, seeded_category: CategoryModel
) -> None:
    repo = SqlAlchemyOfferRepository(db_session)
    await repo.upsert(_make_offer(source_listing_id="a"))
    await repo.upsert(_make_offer(source_listing_id="b"))

    results = await repo.list_by_category("macbook")

    assert len(results) == 2
    assert {o.source_listing_id for o in results} == {"a", "b"}


async def test_get_by_id_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = SqlAlchemyOfferRepository(db_session)
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_list_by_category_paginates_without_gaps_or_duplicates(
    db_session: AsyncSession, seeded_category: CategoryModel
) -> None:
    repo = SqlAlchemyOfferRepository(db_session)
    for i in range(5):
        await repo.upsert(_make_offer(source_listing_id=f"listing-{i}"))

    assert await repo.count_by_category("macbook") == 5

    page1 = await repo.list_by_category("macbook", page=1, page_size=2)
    page2 = await repo.list_by_category("macbook", page=2, page_size=2)
    page3 = await repo.list_by_category("macbook", page=3, page_size=2)

    assert [len(page1), len(page2), len(page3)] == [2, 2, 1]
    seen_ids = {o.id for o in page1} | {o.id for o in page2} | {o.id for o in page3}
    assert len(seen_ids) == 5  # every offer appears exactly once across pages
