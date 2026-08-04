"""Shared behavior contract for any user repository implementation.

Concrete suites (in-memory, SQLAlchemy) inherit this class and supply
only a repository fixture.
"""

import pytest

from app.ports import User, UserRepository


class UserRepositoryContract:
    """Define behavior contract for user repository."""

    @pytest.fixture
    def repository(self) -> UserRepository:
        """Provide a repository implementation."""
        raise NotImplementedError("Subclasses must provide a `repository` fixture")

    @pytest.fixture
    def seeded_user(self) -> User:
        """Provide an existing user."""
        return User(id="user-1", email="user@example.com", hashed_password="hashed")

    @pytest.mark.asyncio
    async def test_should_return_user_when_email_exists(
        self, repository: UserRepository, seeded_user: User
    ) -> None:
        """Return the stored user when its email address exists."""
        assert await repository.get_by_email(seeded_user.email) == seeded_user

    @pytest.mark.asyncio
    async def test_should_return_none_when_email_does_not_exist(
        self, repository: UserRepository
    ) -> None:
        """Return `None` for unknown email."""
        assert await repository.get_by_email("unknown@example.com") is None

    @pytest.mark.asyncio
    async def test_should_return_a_user_record_not_an_orm_entity(
        self, repository: UserRepository, seeded_user: User
    ) -> None:
        """Return a user record, not an ORM entity."""
        result = await repository.get_by_email(seeded_user.email)
        assert type(result) is User
