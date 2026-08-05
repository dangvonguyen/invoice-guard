"""Verify the SQL-backed user repository against its shared contract."""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel
from app.ports import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate
from tests.contracts.user_repository import UserRepositoryContract


@pytest.fixture
def repository(test_db: AsyncSession) -> UserRepository:
    """Return a user repository using the test database session."""
    return UserRepository(session=test_db)


class TestUserRepositoryContract(UserRepositoryContract):
    """Apply the shared repository contract to the SQL implementation."""

    @pytest_asyncio.fixture
    async def repository(
        self, test_db: AsyncSession, seeded_user: User
    ) -> UserRepository:
        """Persist the contract's user and return a repository using that session."""
        test_db.add(
            UserModel(
                id=seeded_user.id,
                email=seeded_user.email,
                hashed_password=seeded_user.hashed_password,
            )
        )
        await test_db.flush()
        return UserRepository(session=test_db)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_should_insert_user(
    test_db: AsyncSession, repository: UserRepository
) -> None:
    """Insert a user and persist all of its fields."""
    user = UserCreate(id="user-1", email="user@example.com", hashed_password="hash-1")

    assert await repository.create(user) is True

    result = await test_db.scalars(
        select(UserModel).where(UserModel.email == "user@example.com")
    )
    stored_users = list(result)

    assert len(stored_users) == 1
    assert stored_users[0].id == user.id
    assert stored_users[0].email == user.email
    assert stored_users[0].hashed_password == user.hashed_password


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_should_ignore_duplicate_email(
    test_db: AsyncSession, repository: UserRepository
) -> None:
    """Report duplicate email creation as a no-op and preserve the first user."""
    first = UserCreate(id="user-1", email="user@example.com", hashed_password="hash-1")
    duplicate = UserCreate(
        id="user-2", email="user@example.com", hashed_password="hash-2"
    )

    assert await repository.create(first) is True
    assert await repository.create(duplicate) is False

    result = await test_db.scalars(
        select(UserModel).where(UserModel.email == "user@example.com")
    )
    stored_users = list(result)

    assert len(stored_users) == 1
    assert stored_users[0].id == first.id
    assert stored_users[0].email == first.email
    assert stored_users[0].hashed_password == first.hashed_password
