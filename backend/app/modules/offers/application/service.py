"""Offers application service — implements `OfferServiceProtocol` (Band 10:
Offers resource group). Read-only: offers are created by the Marketplace
Engine's ingestion pipeline (Task #5), never by this service.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.modules.offers.application.interfaces import OfferRepositoryProtocol
from app.modules.offers.domain.entities import Offer


class OfferService:
    def __init__(self, offers: OfferRepositoryProtocol) -> None:
        self._offers = offers

    async def get_offer(self, offer_id: uuid.UUID) -> Offer:
        offer = await self._offers.get_by_id(offer_id)
        if offer is None:
            raise NotFoundError("offer not found", details={"offer_id": str(offer_id)})
        return offer

    async def list_offers(
        self, *, category: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Offer], int]:
        offers = await self._offers.list_by_category(category, page=page, page_size=page_size)
        total = await self._offers.count_by_category(category)
        return offers, total
