"""Unit tests for app.db.redis.get_redis — no real Redis server needed:
`Redis.from_url` (redis-py) builds a lazily-connecting client, it doesn't
open a socket until the first command is issued."""

from __future__ import annotations

from redis.asyncio import Redis

from app.db.redis import get_redis


def test_get_redis_returns_a_redis_client() -> None:
    get_redis.cache_clear()
    try:
        client = get_redis()
        assert isinstance(client, Redis)
    finally:
        get_redis.cache_clear()


def test_get_redis_is_cached_across_calls() -> None:
    get_redis.cache_clear()
    try:
        first = get_redis()
        second = get_redis()
        assert first is second
    finally:
        get_redis.cache_clear()
