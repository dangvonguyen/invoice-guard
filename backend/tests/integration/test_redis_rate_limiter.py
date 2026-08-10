"""Behavior specifications for Redis-backed invoice upload limiting."""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from testcontainers.community.redis import RedisContainer

from app.core.rate_limit import RedisRateLimiter

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest.fixture(scope="module")
def redis_container() -> Generator[RedisContainer]:
    """Run Redis for this module's rate-limiter specifications."""
    with RedisContainer("redis:7-alpine") as container:
        yield container


@pytest_asyncio.fixture
async def redis(redis_container: RedisContainer) -> AsyncGenerator[Redis]:
    """Provide an isolated async client backed by the Redis container."""
    client = Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(redis_container.port),
        password=redis_container.password,
    )
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()


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
