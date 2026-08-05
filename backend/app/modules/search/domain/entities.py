"""Search domain entities — saved search profiles (Band 01: Saved Searches)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class SearchProfile:
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    category: str
    keywords: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_deal_score: int | None = None
    notify_on_match: bool = True
    is_active: bool = True
