"""Acceptance tests for the login API endpoint."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pwdlib.hashers.argon2 import Argon2Hasher

from app.api.deps import get_user_repository
from app.main import app
from app.ports import User


class InMemoryUserRepository:
    """Store test users in memory and look them up by email address."""

    def __init__(self, users: list[User]) -> None:
        self._users = {u.email: u for u in users}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)


@pytest.fixture
def existing_user() -> User:
    """Create a user with a known password for login tests."""
    password = "secret123"
    hash = Argon2Hasher().hash(password)
    return User(id="user-1", email="user@example.com", hashed_password=hash)


@pytest_asyncio.fixture
async def client(existing_user: User) -> AsyncGenerator[AsyncClient]:
    """Yield a test client configured with the in-memory user repository."""
    fake_repo = InMemoryUserRepository([existing_user])

    app.dependency_overrides[get_user_repository] = lambda: fake_repo

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        try:
            yield ac
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_should_return_access_token_for_valid_credentials(
    client: AsyncClient, existing_user: User
) -> None:
    """Return a bearer token when valid credentials are submitted."""
    response = await client.post(
        "/api/auth/login", json={"email": existing_user.email, "password": "secret123"}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


@pytest.mark.asyncio
async def test_should_reject_login_when_password_is_wrong(
    client: AsyncClient, existing_user: User
) -> None:
    """Reject login attempts with incorrect passwords."""
    response = await client.post(
        "/api/auth/login",
        json={"email": existing_user.email, "password": "wrong-password"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_should_reject_login_when_user_does_not_exist(
    client: AsyncClient,
) -> None:
    """Reject login attempts for unknown users."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "whatever"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
