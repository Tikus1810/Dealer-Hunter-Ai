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


def _unique_event_name() -> str:
    # Never a literal name like "offer_viewed"/"offer_favorited" — those
    # are real event names other integration tests emit for real (e.g.
    # test_analytics_api.py's favoriting test, via the real app's global
    # engine) and *commit*, so a `count_by_name`/`list_recent` on a shared
    # literal name here would pick up rows from whichever other tests
    # happened to run first in the same CI Postgres instance. A random
    # per-test name keeps each test's counts scoped to only what it itself
    # created — same isolation technique as test_rate_limit.py's
    # `key_prefix`.
    return f"test_event_{uuid.uuid4().hex}"


def _event(name: str, user_id: uuid.UUID | None = None) -> AnalyticsEvent:
    return AnalyticsEvent(id=uuid.uuid4(), name=name, user_id=user_id, properties={"k": "v"})


async def test_create_then_list_recent(db_session: AsyncSession) -> None:
    name, other_name = _unique_event_name(), _unique_event_name()
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event(name))
    await repo.create(_event(name))
    await repo.create(_event(other_name))

    recent = await repo.list_recent(name)

    assert len(recent) == 2
    assert all(e.name == name for e in recent)


async def test_list_recent_respects_limit(db_session: AsyncSession) -> None:
    name = _unique_event_name()
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    for _ in range(3):
        await repo.create(_event(name))

    recent = await repo.list_recent(name, limit=2)

    assert len(recent) == 2


async def test_count_by_name_only_counts_the_given_event(db_session: AsyncSession) -> None:
    name, other_name = _unique_event_name(), _unique_event_name()
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event(name))
    await repo.create(_event(other_name))

    assert await repo.count_by_name(name) == 1
    assert await repo.count_by_name(other_name) == 1
    assert await repo.count_by_name(_unique_event_name()) == 0


async def test_count_distinct_users_excludes_anonymous_events(db_session: AsyncSession) -> None:
    name = _unique_event_name()
    users = SqlAlchemyUserRepository(db_session)
    email = f"analytics-user-{uuid.uuid4().hex}@example.com"
    user = await users.create(User(id=uuid.uuid4(), email=email, password_hash="x"))
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event(name, user_id=user.id))
    await repo.create(_event(name, user_id=user.id))  # same user again
    await repo.create(_event(name, user_id=None))  # anonymous

    assert await repo.count_by_name(name) == 3
    assert await repo.count_distinct_users(name) == 1


async def test_purge_older_than_deletes_only_events_before_the_cutoff(
    db_session: AsyncSession,
) -> None:
    name = _unique_event_name()
    repo = SqlAlchemyAnalyticsEventRepository(db_session)
    await repo.create(_event(name))
    await db_session.flush()

    # Everything just created has occurred_at ~= now(); a cutoff in the
    # past should delete nothing, a cutoff in the future should delete it.
    # `purge_older_than` is a deliberately global, unscoped operation (see
    # its own docstring — retention deletes everything old, not one
    # caller's slice of it), so its *count* return value isn't scoped to
    # this test's own event either — a future cutoff matches every row any
    # other test has committed in the same shared CI Postgres instance,
    # not just this one. Assert on this test's own named event via
    # count_by_name (correctly scoped) instead of the raw deleted count.
    deleted_none = await repo.purge_older_than(datetime.now(UTC) - timedelta(days=1))
    assert deleted_none == 0
    assert await repo.count_by_name(name) == 1

    deleted_one = await repo.purge_older_than(datetime.now(UTC) + timedelta(days=1))
    assert deleted_one >= 1
    assert await repo.count_by_name(name) == 0
