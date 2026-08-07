"""Favorites application service — implements `FavoriteServiceProtocol`
(Band 10: Favorites resource group). Kept separate from `OfferService`
since favorites are a distinct concern (user-scoped, mutable) from the
read-only offer catalog — mirrors how DealBrain/RepairBrain each get their
own service despite both consuming `OfferRepositoryProtocol`.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.modules.analytics.application.interfaces import AnalyticsCollectorProtocol
from app.modules.analytics.domain.taxonomy import AnalyticsEventName
from app.modules.offers.application.interfaces import (
    FavoriteRepositoryProtocol,
    OfferRepositoryProtocol,
)
from app.modules.offers.domain.entities import Favorite

logger = get_logger(__name__)


class FavoriteService:
    def __init__(
        self,
        favorites: FavoriteRepositoryProtocol,
        offers: OfferRepositoryProtocol,
        analytics: AnalyticsCollectorProtocol | None = None,
    ) -> None:
        self._favorites = favorites
        self._offers = offers
        self._analytics = analytics

    async def add_favorite(self, user_id: uuid.UUID, offer_id: uuid.UUID) -> Favorite:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            raise NotFoundError("offer not found", details={"offer_id": str(offer_id)})
        if await self._favorites.exists(user_id, offer_id):
            raise ConflictError(
                "offer is already a favorite",
                details={"user_id": str(user_id), "offer_id": str(offer_id)},
            )
        favorite = Favorite(id=uuid.uuid4(), user_id=user_id, offer_id=offer_id)
        created = await self._favorites.add(favorite)
        await self._track(
            AnalyticsEventName.OFFER_FAVORITED,
            user_id=user_id,
            properties={"offer_id": str(offer_id), "category": offer.category.value},
        )
        return created

    async def remove_favorite(self, user_id: uuid.UUID, offer_id: uuid.UUID) -> None:
        if not await self._favorites.exists(user_id, offer_id):
            raise NotFoundError(
                "favorite not found",
                details={"user_id": str(user_id), "offer_id": str(offer_id)},
            )
        await self._favorites.remove(user_id, offer_id)
        await self._track(
            AnalyticsEventName.OFFER_UNFAVORITED,
            user_id=user_id,
            properties={"offer_id": str(offer_id)},
        )

    async def list_favorites(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Favorite], int]:
        favorites = await self._favorites.list_for_user(user_id, page=page, page_size=page_size)
        total = await self._favorites.count_for_user(user_id)
        return favorites, total

    async def _track(
        self, event_name: AnalyticsEventName, *, user_id: uuid.UUID, properties: dict[str, str]
    ) -> None:
        """Best-effort (Band 15): `analytics=None` is the default, every
        existing call site still works unchanged — a tracking failure must
        never fail the favorite/unfavorite action it's observing."""
        if self._analytics is None:
            return
        try:
            await self._analytics.track(event_name.value, user_id=user_id, properties=properties)
        except Exception as exc:  # noqa: BLE001 — never fail the caller over this
            logger.error("analytics_track_failed", event_name=event_name.value, error=str(exc))
