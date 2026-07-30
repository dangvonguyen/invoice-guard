"""Setup the database and support functions."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from pydantic import PostgresDsn
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings, unwrap_secret


def get_database_url() -> str:
    """Return the database URL based on environment."""
    settings = get_settings()
    return PostgresDsn.build(
        scheme="postgresql+asyncpg",
        username=settings.POSTGRES_USER,
        password=unwrap_secret(settings.POSTGRES_PASSWORD),
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        path=settings.POSTGRES_DB,
    ).encoded_string()


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models.

    All other models should inherit from this class.
    """

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the shared async database engine."""
    return create_async_engine(get_database_url(), echo=False)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared factory for creating async database sessions."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield a transactional `AsyncSession` for a single request.

    The session is automatically committed on success, rolled back on
    failure, and closed when the request finishes.
    """
    async with get_session_factory()() as session, session.begin():
        yield session


async def get_session_manual() -> AsyncGenerator[AsyncSession]:
    """Yield an `AsyncSession` with manual transaction control.

    Callers are responsible for explicitly managing transactions by calling
    `commit()` or `rollback()` as appropriate. Any unhandled exception
    triggers a rollback before the session is closed.
    """
    async with get_session_factory()() as session:
        try:
            yield session
        except:
            await session.rollback()
            raise
