"""Specify SQL-backed user persistence and lookup behavior."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.database.repositories.user import UserRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest.fixture
def repository(test_db: AsyncSession) -> UserRepository:
    """Return a user repository using the test database session."""
    return UserRepository(session=test_db)


@pytest.fixture
def existing_user() -> User:
    """Describe a user that already exists in persistent storage."""
    timestamp = datetime(2000, 1, 1, tzinfo=UTC)
    return User(
        id="existing-user",
        email="existing@example.com",
        hashed_password="existing-password-hash",
        name="Existing User",
        role=UserRole.FINANCE_REVIEWER,
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest_asyncio.fixture
async def repository_with_existing_user(
    test_db: AsyncSession, existing_user: User
) -> UserRepository:
    """Return a repository containing the existing user."""
    test_db.add(existing_user)
    await test_db.flush()
    return UserRepository(session=test_db)


async def should_find_existing_user_by_email(
    repository_with_existing_user: UserRepository, existing_user: User
) -> None:
    """Return the stored user whose email address matches."""
    assert (
        await repository_with_existing_user.get_by_email(existing_user.email)
        == existing_user
    )


async def should_return_none_when_email_does_not_match_a_user(
    repository: UserRepository,
) -> None:
    """Return no user when an email address is unknown."""
    assert await repository.get_by_email("unknown@example.com") is None


async def should_find_existing_user_by_id(
    repository_with_existing_user: UserRepository, existing_user: User
) -> None:
    """Return the stored user whose unique ID matches."""
    assert (
        await repository_with_existing_user.get_by_id(existing_user.id) == existing_user
    )


async def should_return_none_when_id_does_not_match_a_user(
    repository: UserRepository,
) -> None:
    """Return no user when an ID is unknown."""
    assert await repository.get_by_id("unknown-user") is None


async def should_persist_new_user(
    test_db: AsyncSession, repository: UserRepository
) -> None:
    """Insert a user and persist all of its fields."""
    user = {
        "id": "user-1",
        "email": "user@example.com",
        "hashed_password": "hash-1",
        "name": "Example User",
        "role": UserRole.EMPLOYEE,
    }

    assert await repository.create(user) is True

    result = await test_db.scalars(select(User).where(User.email == "user@example.com"))
    stored_users = list(result)

    assert len(stored_users) == 1
    assert stored_users[0].id == user["id"]
    assert stored_users[0].email == user["email"]
    assert stored_users[0].hashed_password == user["hashed_password"]
    assert stored_users[0].name == user["name"]
    assert stored_users[0].role == user["role"]


async def should_preserve_existing_user_when_email_is_duplicated(
    test_db: AsyncSession, repository: UserRepository
) -> None:
    """Report duplicate email creation as a no-op and preserve the first user."""
    first = {
        "id": "user-1",
        "email": "user@example.com",
        "hashed_password": "hash-1",
        "name": "First User",
        "role": UserRole.EMPLOYEE,
    }
    duplicate = {
        "id": "user-2",
        "email": "user@example.com",
        "hashed_password": "hash-2",
        "name": "Duplicate User",
        "role": UserRole.FINANCE_REVIEWER,
    }

    assert await repository.create(first) is True
    assert await repository.create(duplicate) is False

    result = await test_db.scalars(select(User).where(User.email == "user@example.com"))
    stored_users = list(result)

    assert len(stored_users) == 1
    assert stored_users[0].id == first["id"]
    assert stored_users[0].email == first["email"]
    assert stored_users[0].hashed_password == first["hashed_password"]
