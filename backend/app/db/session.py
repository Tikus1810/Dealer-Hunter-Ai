"""Async SQLAlchemy engine/session factory + FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )


_engine = build_engine(get_settings())
session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession.

    Unit-of-work per request: commits once the route handler returns
    successfully, rolls back if it raised (including `DomainError`s such as
    `ConflictError`/`NotFoundError`), so route handlers never call
    `session.commit()`/`rollback()` themselves.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
