"""Behavior specifications for Redis-backed invoice upload limiting."""

import pytest
from redis.asyncio import Redis

from app.core.rate_limit import RedisRateLimiter

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


async def should_allow_requests_under_the_threshold(
    redis: Redis,
) -> None:
    """Allow every request while the window's count stays under the limit."""
    limiter = RedisRateLimiter(redis=redis, limit=3, window_seconds=60)

    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is True


async def should_return_false_once_the_bucket_is_exhausted_within_the_window(
    redis: Redis,
) -> None:
    """Reject a request once the per-window cap has been reached."""
    limiter = RedisRateLimiter(redis=redis, limit=2, window_seconds=60)

    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is False


async def should_track_each_key_independently(
    redis: Redis,
) -> None:
    """Isolate one user's exhausted limit from another's fresh one."""
    limiter = RedisRateLimiter(redis=redis, limit=1, window_seconds=60)

    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is False
    assert await limiter.allow("user-2") is True
