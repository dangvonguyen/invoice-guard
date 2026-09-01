"""Shared low-level dependencies: database sessions and the Redis client."""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.database.session import get_session, get_session_manual

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionManualDep = Annotated[AsyncSession, Depends(get_session_manual)]
RedisDep = Annotated[Redis, Depends(get_redis)]
