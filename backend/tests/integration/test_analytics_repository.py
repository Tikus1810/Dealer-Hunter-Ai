"""Integration tests for SqlAlchemyAnalyticsEventRepository. Requires
PostgreSQL (see conftest.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.domain.entities import AnalyticsEvent
from app.modules.analytics.infrastructure.repository import SqlAlchemyAnalyticsEventRepository
from app.modules.users.domain.entities import User
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration


def _event(name: str = "offer_viewed", user_id: uuid.UUID | None = None) -> AnalyticsEvent:
    return AnalyticsEvent(id=uuid.uuid4(), name=name, user_id=user_id, properties={"k": "v"})


async def test_create_then_list_recent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event("offer_viewed"))
    await repo.create(_event("offer_viewed"))
    await repo.create(_event("offer_favorited"))

    recent = await repo.list_recent("offer_viewed")

    assert len(recent) == 2
    assert all(e.name == "offer_viewed" for e in recent)


async def test_list_recent_respects_limit(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    for _ in range(3):
        await repo.create(_event("offer_viewed"))

    recent = await repo.list_recent("offer_viewed", limit=2)

    assert len(recent) == 2


async def test_count_by_name_only_counts_the_given_event(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event("offer_viewed"))
    await repo.create(_event("offer_favorited"))

    assert await repo.count_by_name("offer_viewed") == 1
    assert await repo.count_by_name("offer_favorited") == 1
    assert await repo.count_by_name("nonexistent_event") == 0


async def test_count_distinct_users_excludes_anonymous_events(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    user = await users.create(
        User(id=uuid.uuid4(), email="analytics-user@example.com", password_hash="x")
    )
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event("offer_favorited", user_id=user.id))
    await repo.create(_event("offer_favorited", user_id=user.id))  # same user again
    await repo.create(_event("offer_favorited", user_id=None))  # anonymous

    assert await repo.count_by_name("offer_favorited") == 3
    assert await repo.count_distinct_users("offer_favorited") == 1


async def test_purge_older_than_deletes_only_events_before_the_cutoff(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event("offer_viewed"))
    await db_session.flush()

    # Everything just created has occurred_at ~= now(); a cutoff in the
    # past should delete nothing, a cutoff in the future should delete it.
    deleted_none = await repo.purge_older_than(datetime.now(UTC) - timedelta(days=1))
    assert deleted_none == 0
    assert await repo.count_by_name("offer_viewed") == 1

    deleted_one = await repo.purge_older_than(datetime.now(UTC) + timedelta(days=1))
    assert deleted_one == 1
    assert await repo.count_by_name("offer_viewed") == 0
