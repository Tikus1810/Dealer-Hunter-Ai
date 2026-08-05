"""Public interface of the `auth` module (Band 02: modules expose interfaces only).

Other modules and the presentation layer must depend only on these
Protocols, never on `infrastructure/` internals.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.modules.auth.domain.entities import TokenPair


class AuthServiceProtocol(Protocol):
    async def register(self, *, email: str, password: str) -> uuid.UUID: ...

    async def login(self, *, email: str, password: str) -> TokenPair: ...

    async def refresh(self, *, refresh_token: str) -> TokenPair: ...

    async def logout(self, *, refresh_token: str) -> None: ...


class RefreshTokenRepositoryProtocol(Protocol):
    """Server-side registry of issued refresh tokens, keyed by JWT `jti`.

    Makes token revocation possible for otherwise-stateless JWTs (logout,
    rotation-on-refresh, and future "log out of all devices" support)."""

    async def store(self, *, user_id: uuid.UUID, jti: str, expires_at: datetime) -> None: ...

    async def is_valid(self, jti: str) -> bool: ...

    async def revoke(self, jti: str) -> None: ...
