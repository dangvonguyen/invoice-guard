"""Database fixtures for PostgreSQL integration tests.

The schema and engine are shared for the test session. Each test runs through a
dedicated connection-level transaction that is rolled back during teardown, so
commits made by application code do not leak data into later tests.
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from app.database.db import Base, get_session
from app.main import app


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """Start a session-scoped PostgreSQL container and stop it after the suite."""
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[AsyncEngine]:
    """Create the shared engine and manage the test schema for the session."""
    engine = create_async_engine(
        postgres_container.get_connection_url(), poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def test_connection(test_engine: AsyncEngine) -> AsyncGenerator[AsyncConnection]:
    """Yield a per-test connection whose outer transaction is rolled back."""
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def test_sessionmaker(
    test_connection: AsyncConnection,
) -> async_sessionmaker[AsyncSession]:
    """Create sessions bound to the current test's transactional connection.

    `create_savepoint` makes a session commit release a savepoint while the
    connection's outer transaction remains available for teardown rollback.
    """
    return async_sessionmaker(
        bind=test_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture
async def test_db(
    test_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Yield an async database session and close it after the current test."""
    async with test_sessionmaker() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncGenerator:
    """Yield a test client for the app."""

    async def get_session_override() -> AsyncGenerator[AsyncSession]:
        """Return the database connection for testing."""
        async with test_sessionmaker() as session, session.begin():
            yield session

    app.dependency_overrides[get_session] = get_session_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        try:
            yield ac
        finally:
            app.dependency_overrides.clear()
