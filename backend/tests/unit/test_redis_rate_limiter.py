"""Behavior specifications for Redis-backed invoice upload limiting."""

from collections.abc import AsyncGenerator

import fakeredis
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from app.core.rate_limit import RedisRateLimiter

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def redis() -> AsyncGenerator[FakeRedis]:
    """Provide an isolated in-memory Redis double per test."""
    client = FakeRedis()
    yield client
    await client.aclose()


async def should_allow_requests_under_the_threshold(
    redis: fakeredis.aioredis.FakeRedis,
) -> None:
    """Allow every request while the window's count stays under the limit."""
    limiter = RedisRateLimiter(redis=redis, limit=3, window_seconds=60)

    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is True


async def should_return_false_once_the_bucket_is_exhausted_within_the_window(
    redis: fakeredis.aioredis.FakeRedis,
) -> None:
    """Reject a request once the per-window cap has been reached."""
    limiter = RedisRateLimiter(redis=redis, limit=2, window_seconds=60)

    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is False


async def should_track_each_key_independently(
    redis: fakeredis.aioredis.FakeRedis,
) -> None:
    """Isolate one user's exhausted limit from another's fresh one."""
    limiter = RedisRateLimiter(redis=redis, limit=1, window_seconds=60)

    assert await limiter.allow("user-1") is True
    assert await limiter.allow("user-1") is False
    assert await limiter.allow("user-2") is True
