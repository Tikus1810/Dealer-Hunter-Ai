"""Public interface of the `users` module."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.users.domain.entities import User


class UserRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def create(self, user: User) -> User: ...

    async def update(self, user: User) -> User: ...


class UserServiceProtocol(Protocol):
    async def get_profile(self, user_id: uuid.UUID) -> User: ...

    async def update_profile(self, user_id: uuid.UUID, *, display_name: str) -> User: ...
