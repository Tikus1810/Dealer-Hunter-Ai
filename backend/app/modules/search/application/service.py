"""Search Profiles application service — implements `SearchServiceProtocol`
(Band 10: Search Profiles resource group; Band 01: Saved Searches).

`match_offer_against_profiles` is a v1 heuristic matcher, not a spec-mandated
formula — same honesty note as DealBrain/RepairBrain: category is an exact
match, keywords is a case-insensitive substring check against title+
description, price bounds are inclusive, and `min_deal_score` requires a
persisted DealScore to already exist for the offer (no score yet => that
profile doesn't match, rather than assuming a pass). Profiles with
`notify_on_match=False` are excluded entirely — a user can keep a saved
search around without getting pushes for it. This is what powers Task #10's
notification triggers (see `app.modules.notifications.application.
match_notifier.SavedSearchMatchNotifier`).
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.modules.offers.application.interfaces import OfferRepositoryProtocol
from app.modules.scoring.application.interfaces import DealScoreRepositoryProtocol
from app.modules.search.application.interfaces import SearchProfileRepositoryProtocol
from app.modules.search.domain.entities import SearchProfile


class SearchService:
    def __init__(
        self,
        profiles: SearchProfileRepositoryProtocol,
        offers: OfferRepositoryProtocol,
        deal_scores: DealScoreRepositoryProtocol | None = None,
    ) -> None:
        self._profiles = profiles
        self._offers = offers
        self._deal_scores = deal_scores

    async def create_profile(
        self,
        user_id: uuid.UUID,
        *,
        name: str,
        category: str,
        keywords: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_deal_score: int | None = None,
        notify_on_match: bool = True,
    ) -> SearchProfile:
        profile = SearchProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            category=category,
            keywords=keywords,
            min_price=min_price,
            max_price=max_price,
            min_deal_score=min_deal_score,
            notify_on_match=notify_on_match,
        )
        return await self._profiles.create(profile)

    async def list_my_profiles(self, user_id: uuid.UUID) -> list[SearchProfile]:
        return await self._profiles.list_for_user(user_id)

    async def get_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> SearchProfile:
        profile = await self._profiles.get_by_id(profile_id)
        if profile is None or profile.user_id != user_id:
            raise NotFoundError("search profile not found", details={"profile_id": str(profile_id)})
        return profile

    async def update_profile(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        name: str | None = None,
        category: str | None = None,
        keywords: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_deal_score: int | None = None,
        notify_on_match: bool | None = None,
        is_active: bool | None = None,
    ) -> SearchProfile:
        current = await self.get_profile(user_id, profile_id)  # ownership check
        updated = SearchProfile(
            id=current.id,
            user_id=current.user_id,
            name=name if name is not None else current.name,
            category=category if category is not None else current.category,
            keywords=keywords if keywords is not None else current.keywords,
            min_price=min_price if min_price is not None else current.min_price,
            max_price=max_price if max_price is not None else current.max_price,
            min_deal_score=(
                min_deal_score if min_deal_score is not None else current.min_deal_score
            ),
            notify_on_match=(
                notify_on_match if notify_on_match is not None else current.notify_on_match
            ),
            is_active=is_active if is_active is not None else current.is_active,
        )
        return await self._profiles.update(updated)

    async def delete_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> None:
        await self.get_profile(user_id, profile_id)  # ownership check
        await self._profiles.delete(profile_id)

    async def match_offer_against_profiles(self, offer_id: uuid.UUID) -> list[uuid.UUID]:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            return []

        profiles = await self._profiles.list_active()
        matched: list[uuid.UUID] = []
        deal_score_checked = False
        deal_score_value: int | None = None

        for profile in profiles:
            if not profile.notify_on_match:
                continue
            if profile.category != offer.category.value:
                continue
            if profile.keywords and not self._keywords_match(
                profile.keywords, offer.title, offer.description
            ):
                continue
            if profile.min_price is not None and offer.price_amount < profile.min_price:
                continue
            if profile.max_price is not None and offer.price_amount > profile.max_price:
                continue
            if profile.min_deal_score is not None:
                if not deal_score_checked:
                    deal_score_checked = True
                    if self._deal_scores is not None:
                        latest = await self._deal_scores.get_latest_for_offer(offer_id)
                        deal_score_value = latest.score if latest is not None else None
                if deal_score_value is None or deal_score_value < profile.min_deal_score:
                    continue
            matched.append(profile.id)

        return matched

    @staticmethod
    def _keywords_match(keywords: str, title: str, description: str) -> bool:
        haystack = f"{title} {description}".lower()
        return any(word.strip().lower() in haystack for word in keywords.split() if word.strip())
