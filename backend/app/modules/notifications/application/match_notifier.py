"""Event routing (Band 11): turns "this offer matches these saved
searches" into actual notifications.

Implements `OfferPersistedHookProtocol` (app.modules.offers.application.
interfaces) — the concrete wiring for Band 07's "Trigger Analysis"
extension point. Depends only on other modules' `application/interfaces.py`
(Band 2 module-boundary rule), never their infrastructure, and is itself
constructed and injected at the composition root — the offers module never
imports notifications/search directly.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.core.logging import get_logger
from app.modules.notifications.application.interfaces import NotificationServiceProtocol
from app.modules.notifications.domain.entities import NotificationEvent
from app.modules.offers.domain.entities import Offer
from app.modules.search.application.interfaces import SearchProfileRepositoryProtocol
from app.modules.search.domain.entities import SearchProfile

logger = get_logger(__name__)


class _OfferMatcherProtocol(Protocol):
    """Structural stand-in for the one `SearchServiceProtocol` method this
    notifier needs — avoids depending on the whole search service surface."""

    async def match_offer_against_profiles(self, offer_id: uuid.UUID) -> list[uuid.UUID]: ...


class SavedSearchMatchNotifier:
    """Implements `OfferPersistedHookProtocol`
    (app.modules.offers.application.interfaces)."""

    def __init__(
        self,
        matcher: _OfferMatcherProtocol,
        profiles: SearchProfileRepositoryProtocol,
        notifications: NotificationServiceProtocol,
    ) -> None:
        self._matcher = matcher
        self._profiles = profiles
        self._notifications = notifications

    async def __call__(self, offer: Offer) -> None:
        matched_ids = await self._matcher.match_offer_against_profiles(offer.id)
        for profile_id in matched_ids:
            profile = await self._profiles.get_by_id(profile_id)
            if profile is None:
                continue
            await self._notify_for_profile(profile, offer=offer)

    async def _notify_for_profile(self, profile: SearchProfile, *, offer: Offer) -> None:
        try:
            await self._notifications.notify_user(
                profile.user_id,
                event=NotificationEvent.SAVED_SEARCH_MATCH,
                data={
                    "offer_title": offer.title,
                    "profile_name": profile.name,
                    "price_amount": offer.price_amount,
                },
            )
        except Exception as exc:  # noqa: BLE001 — one user's failure must not block others
            logger.error(
                "saved_search_match_notification_failed",
                profile_id=str(profile.id),
                user_id=str(profile.user_id),
                error=str(exc),
            )
