"""SQLAlchemy implementation of `NotificationPreferenceRepositoryProtocol`
(Band 09/11)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.domain.entities import NotificationPreference
from app.modules.notifications.infrastructure.models import NotificationPreferenceModel


def _to_entity(row: NotificationPreferenceModel) -> NotificationPreference:
    return NotificationPreference(
        user_id=row.user_id, event=row.event, channel=row.channel, enabled=row.enabled
    )


class SqlAlchemyNotificationPreferenceRepository:
    """Implements `NotificationPreferenceRepositoryProtocol`
    (app.modules.notifications.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[NotificationPreference]:
        stmt = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.user_id == user_id
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(row) for row in rows]

    async def upsert(self, preference: NotificationPreference) -> NotificationPreference:
        stmt = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.user_id == preference.user_id,
            NotificationPreferenceModel.event == preference.event,
            NotificationPreferenceModel.channel == preference.channel,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            existing.enabled = preference.enabled
            await self._session.flush()
            await self._session.refresh(existing)
            return _to_entity(existing)

        row = NotificationPreferenceModel(
            user_id=preference.user_id,
            event=preference.event,
            channel=preference.channel,
            enabled=preference.enabled,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)
