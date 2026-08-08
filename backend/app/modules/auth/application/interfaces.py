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
    rotation-on-refresh, and reuse-detection-triggered "log out of every
    device" below)."""

    async def store(self, *, user_id: uuid.UUID, jti: str, expires_at: datetime) -> None: ...

    async def is_valid(self, jti: str) -> bool: ...

    async def is_revoked(self, jti: str) -> bool:
        """True only if `jti` was issued and has since been explicitly
        revoked (rotated out or logged out) — distinct from "never
        existed" or "merely expired", both of which return `False` here.
        `AuthService.refresh` uses this to tell "an unknown/expired token"
        apart from "an already-used token being replayed", since only the
        latter is a signal worth reacting to (see `revoke_all_for_user`
        below)."""
        ...

    async def revoke(self, jti: str) -> None: ...

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke every currently-valid refresh token for `user_id` — "log
        out of every device". Used by `AuthService.refresh`'s reuse-
        detection: the legitimate rotation flow never re-presents a token
        it already exchanged, so a revoked token being presented again is
        a strong signal that token was stolen and is being replayed by
        someone else — the safe response is to invalidate every session
        for that user, not just reject the one replayed request."""
        ...
