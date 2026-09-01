"""Shared RQ queue for background invoice-extraction jobs.

RQ workers pull jobs over a synchronous Redis connection, unlike the async
client in `app.core.redis` used for request-scoped rate limiting.
"""

from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import get_settings

EXTRACTION_QUEUE_NAME = "extraction"


@lru_cache
def get_extraction_queue() -> Queue:
    """Return the shared queue used to enqueue invoice-extraction jobs."""
    settings = get_settings()
    redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    return Queue(EXTRACTION_QUEUE_NAME, connection=redis)
