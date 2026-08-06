"""SQLAlchemy implementation of `NotificationRepositoryProtocol` (Band 09/11).
Doubles as the audit log Band 11 asks for — notifications are append-only,
never deleted, only ever flipped to `is_read`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.infrastructure.models import NotificationModel


def _to_entity(row: NotificationModel) -> Notification:
    return Notification(
        id=row.id,
        user_id=row.user_id,
        event=row.event,
        channel=row.channel,
        title=row.title,
        body=row.body,
        data=row.data,
        is_read=row.is_read,
        created_at=row.created_at,
    )


class SqlAlchemyNotificationRepository:
    """Implements `NotificationRepositoryProtocol`
    (app.modules.notifications.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, notification: Notification) -> Notification:
        row = NotificationModel(
            id=notification.id,
            user_id=notification.user_id,
            event=notification.event,
            channel=notification.channel,
            title=notification.title,
            body=notification.body,
            data=notification.data,
            is_read=notification.is_read,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        row = await self._session.get(NotificationModel, notification_id)
        return _to_entity(row) if row is not None else None

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> list[Notification]:
        offset = max(page - 1, 0) * page_size
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(row) for row in rows]

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(NotificationModel.id)).where(NotificationModel.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one()

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        row = await self._session.get(NotificationModel, notification_id)
        if row is None:
            raise NotFoundError(
                "notification not found", details={"notification_id": str(notification_id)}
            )
        row.is_read = True
        await self._session.flush()
