"""Contract tests for the shared in-memory user repository fake."""

import pytest

from app.ports import User
from tests.contracts.user_repository import UserRepositoryContract
from tests.fakes import InMemoryUserRepository


class TestInMemoryUserRepositoryContract(UserRepositoryContract):
    """Apply the repository contract to :class:`InMemoryUserRepository`."""

    @pytest.fixture
    def repository(self, seeded_user: User) -> InMemoryUserRepository:
        """Provide an in-memory repository containing the seeded test user."""
        return InMemoryUserRepository([seeded_user])
