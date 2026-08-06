"""Unit tests for SearchService against in-memory fakes — no DB, no HTTP."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import NotFoundError
from app.modules.offers.domain.entities import Offer, OfferCategory, OfferSource
from app.modules.scoring.domain.entities import DealScoreResult
from app.modules.search.application.service import SearchService
from app.modules.search.domain.entities import SearchProfile


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


class FakeDealScoreRepository:
    def __init__(self, scores: dict[uuid.UUID, int] | None = None) -> None:
        self._scores = scores or {}

    async def save(self, result: DealScoreResult) -> None:
        raise NotImplementedError

    async def get_latest_for_offer(self, offer_id: uuid.UUID) -> DealScoreResult | None:
        score = self._scores.get(offer_id)
        if score is None:
            return None
        return DealScoreResult(
            offer_id=offer_id,
            score=score,
            confidence=1.0,
            estimated_market_value=1000.0,
            estimated_total_cost=900.0,
            recommendation="buy",
            explanation=[],
            scoring_version="1.0.0",
        )


class FakeSearchProfileRepository:
    def __init__(self) -> None:
        self._profiles: dict[uuid.UUID, SearchProfile] = {}

    async def get_by_id(self, profile_id: uuid.UUID) -> SearchProfile | None:
        return self._profiles.get(profile_id)

    async def list_active(self) -> list[SearchProfile]:
        return [p for p in self._profiles.values() if p.is_active]

    async def list_for_user(self, user_id: uuid.UUID) -> list[SearchProfile]:
        return [p for p in self._profiles.values() if p.user_id == user_id]

    async def create(self, profile: SearchProfile) -> SearchProfile:
        self._profiles[profile.id] = profile
        return profile

    async def update(self, profile: SearchProfile) -> SearchProfile:
        self._profiles[profile.id] = profile
        return profile

    async def delete(self, profile_id: uuid.UUID) -> None:
        self._profiles.pop(profile_id, None)


def _offer(**overrides: object) -> Offer:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": OfferSource.EBAY,
        "source_listing_id": str(uuid.uuid4()),
        "title": "MacBook Pro 14 M3, wie neu",
        "description": "Kaum benutzt, OVP vorhanden.",
        "price_amount": 900.0,
        "price_currency": "EUR",
        "category": OfferCategory.MACBOOK,
        "url": "https://ebay.de/itm/x",
    }
    defaults.update(overrides)
    return Offer(**defaults)  # type: ignore[arg-type]


async def test_create_profile_then_appears_in_list_my_profiles() -> None:
    user_id = uuid.uuid4()
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))

    created = await service.create_profile(user_id, name="MacBooks under 1000", category="macbook")

    profiles = await service.list_my_profiles(user_id)
    assert profiles == [created]


async def test_get_profile_raises_not_found_for_other_users_profile() -> None:
    owner, intruder = uuid.uuid4(), uuid.uuid4()
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))
    created = await service.create_profile(owner, name="mine", category="macbook")

    with pytest.raises(NotFoundError):
        await service.get_profile(intruder, created.id)


async def test_get_profile_raises_not_found_for_unknown_profile() -> None:
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))
    with pytest.raises(NotFoundError):
        await service.get_profile(uuid.uuid4(), uuid.uuid4())


async def test_update_profile_only_changes_provided_fields() -> None:
    user_id = uuid.uuid4()
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))
    created = await service.create_profile(
        user_id, name="original", category="macbook", min_price=500.0
    )

    updated = await service.update_profile(user_id, created.id, name="renamed")

    assert updated.name == "renamed"
    assert updated.category == "macbook"  # untouched
    assert updated.min_price == 500.0  # untouched


async def test_update_profile_raises_not_found_for_other_users_profile() -> None:
    owner, intruder = uuid.uuid4(), uuid.uuid4()
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))
    created = await service.create_profile(owner, name="mine", category="macbook")

    with pytest.raises(NotFoundError):
        await service.update_profile(intruder, created.id, name="hijacked")


async def test_delete_profile_removes_it() -> None:
    user_id = uuid.uuid4()
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))
    created = await service.create_profile(user_id, name="mine", category="macbook")

    await service.delete_profile(user_id, created.id)

    assert await service.list_my_profiles(user_id) == []


async def test_match_offer_against_profiles_requires_category_match() -> None:
    offer = _offer(category=OfferCategory.MACBOOK)
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([offer]))
    await service.create_profile(uuid.uuid4(), name="iphones", category="iphone")

    matches = await service.match_offer_against_profiles(offer.id)

    assert matches == []


async def test_match_offer_against_profiles_matches_on_category_and_price() -> None:
    offer = _offer(category=OfferCategory.MACBOOK, price_amount=800.0)
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([offer]))
    profile = await service.create_profile(
        uuid.uuid4(), name="cheap macbooks", category="macbook", min_price=500.0, max_price=1000.0
    )

    matches = await service.match_offer_against_profiles(offer.id)

    assert matches == [profile.id]


async def test_match_offer_against_profiles_excludes_out_of_price_range() -> None:
    offer = _offer(category=OfferCategory.MACBOOK, price_amount=1500.0)
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([offer]))
    await service.create_profile(
        uuid.uuid4(), name="cheap macbooks", category="macbook", max_price=1000.0
    )

    matches = await service.match_offer_against_profiles(offer.id)

    assert matches == []


async def test_match_offer_against_profiles_checks_keywords() -> None:
    offer = _offer(category=OfferCategory.MACBOOK, title="MacBook Pro 14 M3, wie neu")
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([offer]))
    matching_profile = await service.create_profile(
        uuid.uuid4(), name="pro models", category="macbook", keywords="Pro"
    )
    await service.create_profile(
        uuid.uuid4(), name="air models", category="macbook", keywords="Air"
    )

    matches = await service.match_offer_against_profiles(offer.id)

    assert matches == [matching_profile.id]


async def test_match_offer_against_profiles_requires_deal_score_when_configured() -> None:
    offer = _offer(category=OfferCategory.MACBOOK)
    profiles = FakeSearchProfileRepository()
    # No deal score repository at all => a min_deal_score requirement can never pass.
    service = SearchService(profiles, FakeOfferRepository([offer]))
    await service.create_profile(
        uuid.uuid4(), name="high score", category="macbook", min_deal_score=70
    )

    matches = await service.match_offer_against_profiles(offer.id)

    assert matches == []


async def test_match_offer_against_profiles_passes_when_deal_score_is_high_enough() -> None:
    offer = _offer(category=OfferCategory.MACBOOK)
    profiles = FakeSearchProfileRepository()
    deal_scores = FakeDealScoreRepository({offer.id: 85})
    service = SearchService(profiles, FakeOfferRepository([offer]), deal_scores)
    profile = await service.create_profile(
        uuid.uuid4(), name="high score", category="macbook", min_deal_score=70
    )

    matches = await service.match_offer_against_profiles(offer.id)

    assert matches == [profile.id]


async def test_match_offer_against_profiles_returns_empty_for_unknown_offer() -> None:
    service = SearchService(FakeSearchProfileRepository(), FakeOfferRepository([]))
    matches = await service.match_offer_against_profiles(uuid.uuid4())
    assert matches == []
