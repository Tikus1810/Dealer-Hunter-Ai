"""Offers domain entities — the normalized offer model (Band 07)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class OfferCategory(StrEnum):
    WINDOWS_LAPTOP = "windows_laptop"
    MACBOOK = "macbook"
    IPHONE = "iphone"
    GAME_CONSOLE = "game_console"


class OfferSource(StrEnum):
    EBAY = "ebay"
    EBAY_KLEINANZEIGEN = "ebay_kleinanzeigen"


@dataclass(slots=True)
class Offer:
    """Source-agnostic offer, produced by any MarketplaceProvider (Band 07 pipeline)."""

    id: uuid.UUID
    source: OfferSource
    source_listing_id: str
    title: str
    description: str
    price_amount: float
    price_currency: str
    category: OfferCategory
    images: list[str] = field(default_factory=list)
    location: str | None = None
    seller_name: str | None = None
    seller_rating: float | None = None
    url: str = ""
    created_at: datetime | None = None
    fetched_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RawListing:
    """Provider-native listing data before normalization (Band 07 pipeline step 1-2:
    Provider -> Fetch). `payload` shape depends entirely on `source` — the
    matching branch in `OfferNormalizer` is the only code allowed to read it."""

    source: OfferSource
    source_listing_id: str
    category: OfferCategory
    payload: dict[str, Any]
