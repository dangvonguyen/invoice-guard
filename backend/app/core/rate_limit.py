"""Per-key rate limiting, used to bound cost exposure.

Implementation note: this is a *fixed-window* counter (INCR + EXPIRE NX),
"""

from typing import Protocol, cast
from uuid import UUID

from redis.asyncio import Redis


class RateLimiter(Protocol):
    """Decide whether a keyed action is currently allowed."""

    async def allow(self, owner_id: UUID) -> bool:
        """Return whether the owner may perform another upload."""
        ...


class RedisRateLimiter:
    """Fixed-window rate limiter backed by Redis INCR/EXPIRE."""

    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None:
        """Configure the shared Redis client, cap, and window length."""
        self._redis = redis
        self._limit = limit
        self._window_seconds = window_seconds

    async def allow(self, owner_id: str | UUID) -> bool:
        """Increment the window counter for `key` and enforce the cap."""
        redis_key = f"rate-limit:{owner_id!s}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, self._window_seconds, nx=True)
            count, _ = await pipe.execute()
            count = cast(int, count)
        return count <= self._limit
