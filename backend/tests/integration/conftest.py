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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db import models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base
from app.db.session import build_engine
from app.modules.offers.domain.entities import OfferCategory
from app.modules.offers.infrastructure.models import CategoryModel


@pytest_asyncio.fixture(scope="session")
async def _schema() -> AsyncGenerator[None]:
    """Create all tables once per test session, drop them afterwards."""
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
    category = CategoryModel(code=OfferCategory.MACBOOK.value, name="MacBooks")
    db_session.add(category)
    await db_session.flush()
    return category
