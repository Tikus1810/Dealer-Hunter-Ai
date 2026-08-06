"""Unit tests for app.db.session — build_engine is a pure factory (no
connection opened at construction, SQLAlchemy engines connect lazily);
get_db_session's commit/rollback unit-of-work logic is tested by driving
the async generator directly against a fake session, monkeypatching the
module-level `session_factory` it closes over (no real Postgres needed).
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.db import session as session_module
from app.db.session import build_engine, get_db_session


def test_build_engine_uses_the_configured_database_url() -> None:
    settings = Settings(database_url="postgresql+asyncpg://user:pass@myhost:5432/mydb")
    engine = build_engine(settings)
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.host == "myhost"
    assert engine.url.database == "mydb"


def test_build_engine_echoes_sql_when_app_debug_enabled() -> None:
    assert build_engine(Settings(app_debug=True)).echo is True
    assert build_engine(Settings(app_debug=False)).echo is False


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FakeSessionContextManager:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


async def test_get_db_session_commits_when_the_caller_finishes_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(
        session_module, "session_factory", lambda: _FakeSessionContextManager(fake_session)
    )

    generator = get_db_session()
    yielded = await generator.__anext__()
    # get_db_session is statically typed to yield AsyncSession; the fake
    # deliberately isn't one (duck-typed test double), so this comparison
    # is a real mismatch only to the type checker, not at runtime.
    assert yielded is fake_session  # type: ignore[comparison-overlap]

    # Mirrors FastAPI closing the dependency generator after a successful
    # route handler return.
    with pytest.raises(StopAsyncIteration):
        await generator.__anext__()

    assert fake_session.committed is True
    assert fake_session.rolled_back is False


async def test_get_db_session_rolls_back_and_reraises_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(
        session_module, "session_factory", lambda: _FakeSessionContextManager(fake_session)
    )

    generator = get_db_session()
    await generator.__anext__()

    # Mirrors FastAPI throwing a raised DomainError into the dependency
    # generator at its current suspension point (right after `yield session`).
    with pytest.raises(ValueError, match="boom"):
        await generator.athrow(ValueError("boom"))

    assert fake_session.rolled_back is True
    assert fake_session.committed is False
