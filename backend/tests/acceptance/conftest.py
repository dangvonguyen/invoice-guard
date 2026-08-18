"""Shared fixtures for acceptance scenarios."""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_access_token_codec
from app.database.models.user import User, UserRole


def _bearer_headers(user: User) -> dict[str, str]:
    """Bearer header authenticating as the given user."""
    token = get_access_token_codec().issue(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def employee(test_db: AsyncSession) -> User:
    """Persist a plain employee."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="john@example.com",
        hashed_password="unused-password-hash",
        name="John",
        role=UserRole.EMPLOYEE,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def employee_headers(employee: User) -> dict[str, str]:
    """Bearer header authenticating as the employee."""
    return _bearer_headers(employee)


@pytest_asyncio.fixture
async def other_employee(test_db: AsyncSession) -> User:
    """Persist a second, distinct employee."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        email="jane@example.com",
        hashed_password="unused-password-hash",
        name="Jane",
        role=UserRole.EMPLOYEE,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def other_employee_headers(other_employee: User) -> dict[str, str]:
    """Bearer header authenticating as the other employee."""
    return _bearer_headers(other_employee)


@pytest_asyncio.fixture
async def finance_reviewer(test_db: AsyncSession) -> User:
    """Persist a finance reviewer."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000010"),
        email="alice@example.com",
        hashed_password="unused-password-hash",
        name="Alice",
        role=UserRole.FINANCE_REVIEWER,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def reviewer_headers(finance_reviewer: User) -> dict[str, str]:
    """Bearer header authenticating as the finance_reviewer."""
    return _bearer_headers(finance_reviewer)
