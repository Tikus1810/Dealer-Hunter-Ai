"""Pydantic v2 DTOs for the Offers and Favorites API (Band 10)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class OfferResponse(BaseModel):
    id: uuid.UUID
    source: str
    source_listing_id: str
    title: str
    description: str
    price_amount: float
    price_currency: str
    category: str
    images: list[str]
    location: str | None
    url: str
    created_at: datetime | None
    fetched_at: datetime | None


class OfferListResponse(BaseModel):
    items: list[OfferResponse]
    total: int
    page: int
    page_size: int


class FavoriteResponse(BaseModel):
    id: uuid.UUID
    offer_id: uuid.UUID
    created_at: datetime | None


class FavoriteListResponse(BaseModel):
    items: list[FavoriteResponse]
    total: int
    page: int
    page_size: int
