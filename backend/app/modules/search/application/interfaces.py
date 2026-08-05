"""Public interface of the `search` module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.search.domain.entities import SearchProfile


class SearchProfileRepositoryProtocol(Protocol):
    async def get_by_id(self, profile_id: uuid.UUID) -> SearchProfile | None: ...

    async def list_active(self) -> list[SearchProfile]: ...

    async def create(self, profile: SearchProfile) -> SearchProfile: ...


class SearchServiceProtocol(Protocol):
    async def create_profile(self, user_id: uuid.UUID, **fields: object) -> SearchProfile: ...

    async def match_offer_against_profiles(self, offer_id: uuid.UUID) -> list[uuid.UUID]:
        """Return ids of SearchProfiles this offer matches (used to trigger notifications)."""
        ...
