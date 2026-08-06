"""Pydantic v2 DTOs for the Search Profiles API (Band 10)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class CreateSearchProfileRequest(BaseModel):
    name: str
    category: str
    keywords: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_deal_score: int | None = None
    notify_on_match: bool = True


class UpdateSearchProfileRequest(BaseModel):
    """All fields optional — only non-null fields are applied (see
    `SearchServiceProtocol.update_profile`'s docstring for the v1 limitation
    that an optional field already set cannot be cleared this way)."""

    name: str | None = None
    category: str | None = None
    keywords: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_deal_score: int | None = None
    notify_on_match: bool | None = None
    is_active: bool | None = None


class SearchProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    keywords: str | None
    min_price: float | None
    max_price: float | None
    min_deal_score: int | None
    notify_on_match: bool
    is_active: bool
