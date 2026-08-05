"""Public interface of the `offers` module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.offers.domain.entities import Offer


class OfferRepositoryProtocol(Protocol):
    async def get_by_id(self, offer_id: uuid.UUID) -> Offer | None: ...

    async def exists_by_source(self, source: str, source_listing_id: str) -> bool: ...

    async def upsert(self, offer: Offer) -> Offer: ...

    async def list_by_category(
        self, category: str, *, limit: int = 20, cursor: str | None = None
    ) -> list[Offer]: ...


class OfferServiceProtocol(Protocol):
    async def get_offer(self, offer_id: uuid.UUID) -> Offer: ...

    async def search_offers(self, *, category: str, query: str | None = None) -> list[Offer]: ...
