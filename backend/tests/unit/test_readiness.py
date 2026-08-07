"""Unit tests for GET /api/v1/ready (Band 13: Deployment/DevOps —
Monitoring). `app.main.session_factory`/`get_redis` are monkeypatched to
fakes so this needs no real Postgres/Redis — the real-dependency path is
covered by tests/integration/test_readiness.py against the CI services.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app import main as main_module
from app.main import app


class _OkSession:
    async def execute(self, *args: object, **kwargs: object) -> None:
        return None

    async def __aenter__(self) -> _OkSession:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class _FailingSession:
    async def execute(self, *args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("db is down")

    async def __aenter__(self) -> _FailingSession:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class _OkRedis:
    async def ping(self) -> bool:
        return True


class _FailingRedis:
    async def ping(self) -> bool:
        raise RedisError("redis is down")


async def test_ready_returns_200_when_database_and_redis_are_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "session_factory", lambda: _OkSession())
    monkeypatch.setattr(main_module, "get_redis", lambda: _OkRedis())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "ok"}


async def test_ready_returns_503_when_database_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "session_factory", lambda: _FailingSession())
    monkeypatch.setattr(main_module, "get_redis", lambda: _OkRedis())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["redis"] == "ok"
    assert "db is down" in body["checks"]["database"]


async def test_ready_returns_503_when_redis_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "session_factory", lambda: _OkSession())
    monkeypatch.setattr(main_module, "get_redis", lambda: _FailingRedis())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["checks"]["database"] == "ok"
    assert "redis is down" in body["checks"]["redis"]
