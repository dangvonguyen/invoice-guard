"""Acceptance tests for the current-user endpoint."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.adapters.jwt_tokens import JwtAccessTokenCodec
from app.api.deps import get_access_token_codec, get_user_repository
from app.main import app
from app.ports import User
from tests.fakes import InMemoryUserRepository


@pytest.fixture
def existing_user() -> User:
    """Provide a persisted user profile."""
    return User(id="user-1", email="user@example.com", hashed_password="secret-hash")


@pytest.fixture
def token_issuer() -> JwtAccessTokenCodec:
    """Provide a codec for issuing access tokens."""
    return get_access_token_codec()


@pytest_asyncio.fixture
async def client(
    existing_user: User, token_issuer: JwtAccessTokenCodec
) -> AsyncGenerator[AsyncClient]:
    """Yield an API client backed by an in-memory user repository."""
    repository = InMemoryUserRepository([existing_user])

    app.dependency_overrides[get_user_repository] = lambda: repository
    app.dependency_overrides[get_access_token_codec] = lambda: token_issuer
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        try:
            yield ac
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_should_return_safe_current_user_profile(
    client: AsyncClient, existing_user: User, token_issuer: JwtAccessTokenCodec
) -> None:
    """Return identity fields without exposing the password hash."""
    token = token_issuer.issue(existing_user.id)

    response = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == existing_user.id
    assert body["email"] == existing_user.email
    assert "hashed_password" not in body
