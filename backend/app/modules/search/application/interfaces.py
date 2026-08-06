"""Public interface of the `search` module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.search.domain.entities import SearchProfile


class SearchProfileRepositoryProtocol(Protocol):
    async def get_by_id(self, profile_id: uuid.UUID) -> SearchProfile | None: ...

    async def list_active(self) -> list[SearchProfile]: ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[SearchProfile]: ...

    async def create(self, profile: SearchProfile) -> SearchProfile: ...

    async def update(self, profile: SearchProfile) -> SearchProfile: ...

    async def delete(self, profile_id: uuid.UUID) -> None: ...


class SearchServiceProtocol(Protocol):
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
    ) -> SearchProfile: ...

    async def list_my_profiles(self, user_id: uuid.UUID) -> list[SearchProfile]: ...

    async def get_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> SearchProfile:
        """Raises NotFoundError if the profile doesn't exist or isn't owned by
        user_id — both cases return the same error to avoid enumeration."""
        ...

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
        """Only fields explicitly passed (non-None) are changed — a v1
        limitation is that an already-set optional field (e.g. keywords)
        cannot be cleared back to null via this signature, only replaced."""
        ...

    async def delete_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> None: ...

    async def match_offer_against_profiles(self, offer_id: uuid.UUID) -> list[uuid.UUID]:
        """Return ids of SearchProfiles this offer matches (used to trigger notifications)."""
        ...
