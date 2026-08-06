"""Unit tests for FavoriteService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.offers.application.favorite_service import FavoriteService
from app.modules.offers.domain.entities import Favorite, Offer, OfferCategory, OfferSource


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
        raise NotImplementedError

    async def count_by_category(self, category: str) -> int:
        raise NotImplementedError


class FakeFavoriteRepository:
    def __init__(self) -> None:
        self._favorites: dict[tuple[uuid.UUID, uuid.UUID], Favorite] = {}

    async def add(self, favorite: Favorite) -> Favorite:
        self._favorites[(favorite.user_id, favorite.offer_id)] = favorite
        return favorite

    async def remove(self, user_id: uuid.UUID, offer_id: uuid.UUID) -> None:
        self._favorites.pop((user_id, offer_id), None)

    async def exists(self, user_id: uuid.UUID, offer_id: uuid.UUID) -> bool:
        return (user_id, offer_id) in self._favorites

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> list[Favorite]:
        matching = [f for f in self._favorites.values() if f.user_id == user_id]
        offset = max(page - 1, 0) * page_size
        return matching[offset : offset + page_size]

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        return len([f for f in self._favorites.values() if f.user_id == user_id])


def _offer() -> Offer:
    return Offer(
        id=uuid.uuid4(),
        source=OfferSource.EBAY,
        source_listing_id=str(uuid.uuid4()),
        title="MacBook Pro 14 M3",
        description="Wie neu.",
        price_amount=900.0,
        price_currency="EUR",
        category=OfferCategory.MACBOOK,
        url="https://ebay.de/itm/x",
    )


async def test_add_favorite_succeeds_for_existing_offer() -> None:
    offer = _offer()
    user_id = uuid.uuid4()
    service = FavoriteService(FakeFavoriteRepository(), FakeOfferRepository([offer]))

    favorite = await service.add_favorite(user_id, offer.id)

    assert favorite.user_id == user_id
    assert favorite.offer_id == offer.id


async def test_add_favorite_raises_not_found_for_unknown_offer() -> None:
    service = FavoriteService(FakeFavoriteRepository(), FakeOfferRepository([]))
    with pytest.raises(NotFoundError):
        await service.add_favorite(uuid.uuid4(), uuid.uuid4())


async def test_add_favorite_twice_raises_conflict() -> None:
    offer = _offer()
    user_id = uuid.uuid4()
    service = FavoriteService(FakeFavoriteRepository(), FakeOfferRepository([offer]))
    await service.add_favorite(user_id, offer.id)

    with pytest.raises(ConflictError):
        await service.add_favorite(user_id, offer.id)


async def test_remove_favorite_removes_it() -> None:
    offer = _offer()
    user_id = uuid.uuid4()
    service = FavoriteService(FakeFavoriteRepository(), FakeOfferRepository([offer]))
    await service.add_favorite(user_id, offer.id)

    await service.remove_favorite(user_id, offer.id)

    favorites, total = await service.list_favorites(user_id)
    assert total == 0
    assert favorites == []


async def test_remove_favorite_raises_not_found_when_absent() -> None:
    service = FavoriteService(FakeFavoriteRepository(), FakeOfferRepository([]))
    with pytest.raises(NotFoundError):
        await service.remove_favorite(uuid.uuid4(), uuid.uuid4())


async def test_list_favorites_only_returns_the_given_users_favorites() -> None:
    offer_a, offer_b = _offer(), _offer()
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    service = FavoriteService(FakeFavoriteRepository(), FakeOfferRepository([offer_a, offer_b]))
    await service.add_favorite(user_a, offer_a.id)
    await service.add_favorite(user_b, offer_b.id)

    favorites, total = await service.list_favorites(user_a)

    assert total == 1
    assert favorites[0].offer_id == offer_a.id
