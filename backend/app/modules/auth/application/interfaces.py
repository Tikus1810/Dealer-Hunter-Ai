"""Public interface of the `auth` module (Band 02: modules expose interfaces only).

Other modules and the presentation layer must depend only on this Protocol,
never on `infrastructure/` internals.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.auth.domain.entities import TokenPair


class AuthServiceProtocol(Protocol):
    async def register(self, *, email: str, password: str) -> uuid.UUID: ...

    async def login(self, *, email: str, password: str) -> TokenPair: ...

    async def refresh(self, *, refresh_token: str) -> TokenPair: ...

    async def logout(self, *, refresh_token: str) -> None: ...
