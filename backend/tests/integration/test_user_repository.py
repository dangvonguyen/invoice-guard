"""Verify the SQL-backed user repository against its shared contract."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User as UserModel
from app.ports import User
from app.repositories.user import UserRepository
from tests.contracts.user_repository import UserRepositoryContract


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
