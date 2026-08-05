"""Users application service — implements `UserServiceProtocol`."""

from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.modules.users.application.interfaces import UserRepositoryProtocol
from app.modules.users.domain.entities import User


class UserService:
    def __init__(self, users: UserRepositoryProtocol) -> None:
        self._users = users

    async def get_profile(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found", details={"user_id": str(user_id)})
        return user

    async def update_profile(self, user_id: uuid.UUID, *, display_name: str) -> User:
        user = await self.get_profile(user_id)
        user.display_name = display_name
        return await self._users.update(user)
