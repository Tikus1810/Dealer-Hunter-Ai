"""SQLAlchemy implementation of `AnalyticsEventRepositoryProtocol` (Band 09/15)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.domain.entities import AnalyticsEvent
from app.modules.analytics.infrastructure.models import AnalyticsEventModel


def _to_entity(row: AnalyticsEventModel) -> AnalyticsEvent:
    return AnalyticsEvent(
        id=row.id,
        name=row.name,
        user_id=row.user_id,
        properties=dict(row.properties),
        occurred_at=row.occurred_at,
    )


class SqlAlchemyAnalyticsEventRepository:
    """Implements `AnalyticsEventRepositoryProtocol`
    (app.modules.analytics.application.interfaces)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: AnalyticsEvent) -> AnalyticsEvent:
        row = AnalyticsEventModel(
            id=event.id, name=event.name, user_id=event.user_id, properties=event.properties
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def list_recent(self, name: str, *, limit: int = 100) -> list[AnalyticsEvent]:
        stmt = (
            select(AnalyticsEventModel)
            .where(AnalyticsEventModel.name == name)
            .order_by(AnalyticsEventModel.occurred_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(row) for row in rows]

    async def count_by_name(self, name: str, *, since: datetime | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(AnalyticsEventModel)
            .where(AnalyticsEventModel.name == name)
        )
        if since is not None:
            stmt = stmt.where(AnalyticsEventModel.occurred_at >= since)
        return (await self._session.execute(stmt)).scalar_one()

    async def count_distinct_users(self, name: str, *, since: datetime | None = None) -> int:
        # Anonymous events (user_id IS NULL) don't count toward reach —
        # NULL never matches itself in a DISTINCT count, but excluding it
        # explicitly documents the intent rather than relying on that.
        stmt = (
            select(func.count(func.distinct(AnalyticsEventModel.user_id)))
            .where(AnalyticsEventModel.name == name)
            .where(AnalyticsEventModel.user_id.is_not(None))
        )
        if since is not None:
            stmt = stmt.where(AnalyticsEventModel.occurred_at >= since)
        return (await self._session.execute(stmt)).scalar_one()

    async def purge_older_than(self, cutoff: datetime) -> int:
        stmt = delete(AnalyticsEventModel).where(AnalyticsEventModel.occurred_at < cutoff)
        result = await self._session.execute(stmt)
        return result.rowcount or 0
