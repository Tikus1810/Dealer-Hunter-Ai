"""Unit tests for the Redis-backed rate limiter (Band 14: Security-Härtung).
`_FakeRedis` implements just `incr`/`expire` — no real Redis needed.
"""

from __future__ import annotations

import pytest

import app.core.rate_limit as rate_limit_module
from app.core.config import Settings
from app.core.exceptions import RateLimitedError
from app.core.rate_limit import RateLimiter, rate_limit


class _FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expired: dict[str, int] = {}

    async def incr(self, name: str) -> int:
        self.counts[name] = self.counts.get(name, 0) + 1
        return self.counts[name]

    async def expire(self, name: str, seconds: int) -> bool:
        self.expired[name] = seconds
        return True


async def test_check_allows_requests_within_the_limit() -> None:
    limiter = RateLimiter(_FakeRedis(), key_prefix="login", limit=3, window_seconds=60)

    for _ in range(3):
        await limiter.check("1.2.3.4")  # must not raise


async def test_check_raises_once_the_limit_is_exceeded() -> None:
    limiter = RateLimiter(_FakeRedis(), key_prefix="login", limit=2, window_seconds=60)

    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    with pytest.raises(RateLimitedError):
        await limiter.check("1.2.3.4")


async def test_check_sets_expiry_only_on_the_first_hit_in_a_window() -> None:
    redis = _FakeRedis()
    limiter = RateLimiter(redis, key_prefix="login", limit=5, window_seconds=42)

    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")

    # Only recorded once — a second `expire` call on the same hit would
    # keep pushing the window out and it would never close.
    assert redis.expired == {"ratelimit:login:1.2.3.4": 42}


async def test_check_tracks_identifiers_independently() -> None:
    limiter = RateLimiter(_FakeRedis(), key_prefix="login", limit=1, window_seconds=60)

    await limiter.check("1.1.1.1")  # must not raise
    await limiter.check("2.2.2.2")  # different identifier — must not raise
    with pytest.raises(RateLimitedError):
        await limiter.check("1.1.1.1")  # same identifier again — over limit


async def test_check_tracks_key_prefixes_independently() -> None:
    redis = _FakeRedis()
    login_limiter = RateLimiter(redis, key_prefix="login", limit=1, window_seconds=60)
    register_limiter = RateLimiter(redis, key_prefix="register", limit=1, window_seconds=60)

    await login_limiter.check("1.2.3.4")
    await register_limiter.check("1.2.3.4")  # same IP, different endpoint — must not raise


class _FakeRequestClient:
    def __init__(self, host: str) -> None:
        self.host = host


class _FakeRequest:
    def __init__(self, host: str | None) -> None:
        self.client = _FakeRequestClient(host) if host is not None else None


async def test_dependency_is_a_noop_when_rate_limiting_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rate_limit_module, "get_settings", lambda: Settings(rate_limit_enabled=False)
    )
    dependency = rate_limit("login", limit=1, window_seconds=60)

    # Would raise on the second call if this actually enforced the limit.
    await dependency(_FakeRequest("1.2.3.4"))  # type: ignore[arg-type]
    await dependency(_FakeRequest("1.2.3.4"))  # type: ignore[arg-type]


async def test_dependency_enforces_the_limit_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(
        rate_limit_module, "get_settings", lambda: Settings(rate_limit_enabled=True)
    )
    monkeypatch.setattr(rate_limit_module, "get_redis", lambda: fake_redis)
    dependency = rate_limit("login", limit=1, window_seconds=60)

    await dependency(_FakeRequest("1.2.3.4"))  # type: ignore[arg-type]
    with pytest.raises(RateLimitedError):
        await dependency(_FakeRequest("1.2.3.4"))  # type: ignore[arg-type]


async def test_dependency_falls_back_to_a_placeholder_identifier_without_a_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(
        rate_limit_module, "get_settings", lambda: Settings(rate_limit_enabled=True)
    )
    monkeypatch.setattr(rate_limit_module, "get_redis", lambda: fake_redis)
    dependency = rate_limit("login", limit=1, window_seconds=60)

    await dependency(_FakeRequest(None))  # type: ignore[arg-type]  # must not crash

    assert "ratelimit:login:unknown" in fake_redis.counts
