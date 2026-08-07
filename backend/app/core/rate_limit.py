"""Redis-backed rate limiting (Band 14: Security-Härtung — OWASP API4:2023
"Unrestricted Resource Consumption"). Targets brute-force/credential-
stuffing against the unauthenticated auth endpoints (register/login/
refresh) specifically, not a general-purpose API gateway rate limiter.

Fixed-window counter: `INCR` a per-identifier-per-window Redis key, set it
to expire after the window on its first hit, reject once the count exceeds
the configured limit within that window. This allows a burst of up to ~2x
the limit right across a window boundary (a client maxes out the tail of
one window and the head of the next) — a real tradeoff against a sliding-
window/token-bucket algorithm, accepted here because it's O(1) Redis ops
per request with no extra state, and "blunt but correct in the common
case" is enough for its actual job.

Off by default (`RATE_LIMIT_ENABLED=false`) — same reasoning as every other
optional integration in this codebase (FCM/Claude/eBay/the scheduler): the
existing integration test suite calls `/auth/login`/`/auth/register`
dozens of times across test files sharing one Redis instance and one
synthetic client IP (httpx's `ASGITransport`), which would trip a naive
default-on limiter and fail unrelated tests. Enable it explicitly once
something (a real deployment, or a dedicated test) actually wants it
enforced.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError
from app.db.redis import get_redis


class RedisCounterProtocol(Protocol):
    """Structural stand-in for the two `redis.asyncio.Redis` methods this
    needs — lets tests pass an in-memory fake instead of a real Redis.
    Declared as plain (non-`async def`) methods returning `Awaitable[Any]`,
    not `int`/`bool`-returning coroutines, to match redis-py's own stubs
    closely enough: its sync/async clients share codegen'd method
    signatures typed as `Awaitable[Any] | Any`, which a `Coroutine[Any,
    Any, int]` (what an `async def ... -> int` protocol method desugars
    to) isn't assignable from — real `async def` fakes in tests still
    satisfy this fine, since a coroutine is itself an `Awaitable`."""

    def incr(self, name: str, /) -> Awaitable[Any]: ...
    def expire(self, name: str, seconds: int, /) -> Awaitable[Any]: ...


class RateLimiter:
    def __init__(
        self,
        redis: RedisCounterProtocol,
        *,
        key_prefix: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        self._redis = redis
        self._key_prefix = key_prefix
        self._limit = limit
        self._window_seconds = window_seconds

    async def check(self, identifier: str) -> None:
        """Raises `RateLimitedError` if `identifier` has exceeded `limit`
        requests within the current window."""
        key = f"ratelimit:{self._key_prefix}:{identifier}"
        count = await self._redis.incr(key)
        if count == 1:
            # Only the request that created the key sets its TTL — every
            # later `incr` in the same window must not keep pushing the
            # expiry back out, or the window would never actually close.
            await self._redis.expire(key, self._window_seconds)
        if count > self._limit:
            raise RateLimitedError(
                f"rate limit exceeded: more than {self._limit} requests in "
                f"{self._window_seconds}s",
                details={"key_prefix": self._key_prefix, "limit": self._limit},
            )


def rate_limit(
    key_prefix: str, *, limit: int, window_seconds: int
) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency factory — `dependencies=[Depends(rate_limit(...))]`
    on a route. Identifies callers by client IP: these are unauthenticated
    endpoints (that's the whole point — register/login/refresh happen
    before any token exists), so there's no other stable per-caller
    identifier available yet."""

    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        client_ip = request.client.host if request.client is not None else "unknown"
        limiter = RateLimiter(
            get_redis(), key_prefix=key_prefix, limit=limit, window_seconds=window_seconds
        )
        await limiter.check(client_ip)

    return dependency
