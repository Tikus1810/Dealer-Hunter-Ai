"""SQLAlchemy implementation of `DeviceTokenRepositoryProtocol` (Band 09/11)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.domain.entities import DeviceToken
from app.modules.notifications.infrastructure.models import DeviceTokenModel


def _to_entity(row: DeviceTokenModel) -> DeviceToken:
    return DeviceToken(
        id=row.id,
        user_id=row.user_id,
        token=row.token,
        platform=row.platform,
        is_active=row.is_active,
        created_at=row.created_at,
    )


class SqlAlchemyDeviceTokenRepository:
    """Implements `DeviceTokenRepositoryProtocol`
    (app.modules.notifications.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, device_token: DeviceToken) -> DeviceToken:
        stmt = select(DeviceTokenModel).where(DeviceTokenModel.token == device_token.token)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            # Same physical device re-registering (possibly under a
            # different account) — reassign + reactivate rather than insert
            # a second row for the same token.
            existing.user_id = device_token.user_id
            existing.platform = device_token.platform
            existing.is_active = True
            await self._session.flush()
            await self._session.refresh(existing)
            return _to_entity(existing)

        row = DeviceTokenModel(
            id=device_token.id,
            user_id=device_token.user_id,
            token=device_token.token,
            platform=device_token.platform,
            is_active=True,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def deactivate(self, user_id: uuid.UUID, token: str) -> None:
        stmt = select(DeviceTokenModel).where(
            DeviceTokenModel.user_id == user_id, DeviceTokenModel.token == token
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            row.is_active = False
            await self._session.flush()

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[DeviceToken]:
        stmt = select(DeviceTokenModel).where(
            DeviceTokenModel.user_id == user_id, DeviceTokenModel.is_active.is_(True)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(row) for row in rows]
