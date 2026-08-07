"""Fixtures for database integration tests.

Requires a reachable PostgreSQL instance at `settings.database_url` (see
`infra/docker/docker-compose.yml` for local dev, or the `postgres` service
in `.github/workflows/ci.yml` for CI). Each test runs inside a transaction
that is rolled back afterwards, so tests never leave data behind or depend
on each other's state.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db import models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base
from app.db.redis import get_redis
from app.db.session import build_engine, session_factory
from app.modules.offers.domain.entities import OfferCategory
from app.modules.offers.infrastructure.models import CategoryModel


@pytest_asyncio.fixture(autouse=True)
async def _reset_process_singletons_per_test() -> AsyncGenerator[None]:
    """`app.db.session`'s module-level engine and `app.db.redis.get_redis()`'s
    `@lru_cache`d client are process singletons — correct for production
    (one process, one event loop for its whole life) but each becomes
    bound to whichever event loop first opens a connection through it.
    pytest-asyncio gives each test *function* its own event loop by
    default; several integration tests deliberately exercise the real
    global `app.main.app` over HTTP (see e.g. test_offers_api.py's own
    comment on why), which touches both singletons — reusing either in a
    later test's different loop raises `RuntimeError: ... attached to a
    different loop` / `Event loop is closed`. Clearing/disposing both
    between every test forces a fresh connection under whichever loop is
    currently active, rather than routing tests around the real app.
    """
    get_redis.cache_clear()
    yield
    get_redis.cache_clear()
    await session_factory.kw["bind"].dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _schema() -> AsyncGenerator[None]:
    """Create all tables once per test session, drop them afterwards.

    `loop_scope="session"` (separate from the fixture's own `scope`, a
    pytest-asyncio 0.24+ feature) is required here: `pyproject.toml` sets
    `asyncio_default_fixture_loop_scope = "function"` (Task #13) for every
    *other* fixture/test, but a session-scoped async fixture can't run
    under a function-scoped event loop that gets torn down after the first
    test — pytest-asyncio raises `ScopeMismatch` otherwise. This was never
    caught locally (no Postgres available in the sandbox that wrote these
    fixtures — see the module docstring) or in CI until the first real run
    against this repo's actual GitHub remote.
    """
    engine = build_engine(get_settings())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_schema: None) -> AsyncGenerator[AsyncSession]:
    """A session bound to a connection-level transaction that is always rolled back."""
    engine = build_engine(get_settings())
    async with engine.connect() as conn:
        trans = await conn.begin()
        session_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_category(db_session: AsyncSession) -> CategoryModel:
    """Idempotent, not a bare INSERT: several other integration test files
    seed the same category `code` through the real global `session_factory`
    engine and commit it for real (deliberately — they test through the
    real HTTP app), so it can already exist as a permanent row in the
    shared CI Postgres instance by the time this fixture runs, independent
    of this fixture's own `db_session` transaction being rolled back. A
    bare INSERT here raced a real `UniqueViolationError` against whichever
    test happened to run first — never caught locally (no Postgres), only
    surfaced the first time every integration test ran together for real."""
    existing = (
        await db_session.execute(
            select(CategoryModel).where(CategoryModel.code == OfferCategory.MACBOOK.value)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    category = CategoryModel(code=OfferCategory.MACBOOK.value, name="MacBooks")
    db_session.add(category)
    await db_session.flush()
    return category
