"""Shared Redis client for rate-limiting use."""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    """Return the shared async Redis client."""
    settings = get_settings()
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
