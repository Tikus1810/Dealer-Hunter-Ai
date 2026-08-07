"""Integration test for the rate limiter against real Redis (Band 14:
Security-Härtung) — tests/unit/test_rate_limit.py covers the counting/
raising logic against an in-memory fake; this proves the real `INCR`/
`EXPIRE` Redis commands behave the same way.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import RateLimitedError
from app.core.rate_limit import RateLimiter
from app.db.redis import get_redis

pytestmark = pytest.mark.integration


async def test_rate_limiter_enforces_the_limit_against_real_redis() -> None:
    # A random key prefix isolates this test from anything else that might
    # touch the same Redis instance in the same CI run — real Redis state
    # outlives a single test, unlike the fakes in the unit-test version.
    key_prefix = f"test-{uuid.uuid4().hex}"
    limiter = RateLimiter(get_redis(), key_prefix=key_prefix, limit=2, window_seconds=5)

    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    with pytest.raises(RateLimitedError):
        await limiter.check("1.2.3.4")


async def test_rate_limiter_window_expires_via_real_redis_ttl() -> None:
    key_prefix = f"test-{uuid.uuid4().hex}"
    limiter = RateLimiter(get_redis(), key_prefix=key_prefix, limit=1, window_seconds=1)

    await limiter.check("5.6.7.8")
    with pytest.raises(RateLimitedError):
        await limiter.check("5.6.7.8")

    key = f"ratelimit:{key_prefix}:5.6.7.8"
    ttl = await get_redis().ttl(key)
    assert 0 < ttl <= 1
