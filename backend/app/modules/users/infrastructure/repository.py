"""SQLAlchemy implementation of `UserRepositoryProtocol` (Band 03: Repository Pattern)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.entities import User
from app.modules.users.infrastructure.models import UserModel


def _to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        display_name=row.display_name,
        is_active=row.is_active,
        is_admin=row.is_admin,
        created_at=row.created_at,
        updated_at=row.updated_at,
        roles=list(row.roles),
    )


class SqlAlchemyUserRepository:
    """Implements `UserRepositoryProtocol` (app.modules.users.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return _to_entity(row) if row and not row.is_deleted else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email, UserModel.deleted_at.is_(None))
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(row) if row else None

    async def create(self, user: User) -> User:
        row = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            display_name=user.display_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            roles=user.roles,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def update(self, user: User) -> User:
        row = await self._session.get(UserModel, user.id)
        if row is None:
            raise ValueError(f"user {user.id} not found")
        row.display_name = user.display_name
        row.is_active = user.is_active
        row.is_admin = user.is_admin
        row.roles = user.roles
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def update_password_hash(self, user_id: uuid.UUID, *, password_hash: str) -> None:
        row = await self._session.get(UserModel, user_id)
        if row is None:
            raise ValueError(f"user {user_id} not found")
        row.password_hash = password_hash
        await self._session.flush()
