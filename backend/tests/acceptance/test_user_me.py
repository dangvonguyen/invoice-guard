"""Acceptance scenarios for retrieving profiles with bearer authentication."""

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_access_token_codec
from app.core.security import JwtAccessTokenCodec
from app.database.models.user import User

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def registered_user(test_db: AsyncSession) -> User:
    """Persist the profile returned to an authenticated account."""
    user = User(
        id="user-1",
        email="user@example.com",
        hashed_password="secret-hash",
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def token_issuer() -> JwtAccessTokenCodec:
    """Provide a codec for issuing access tokens."""
    return get_access_token_codec()


async def should_return_authenticated_users_profile_without_password_hash(
    client: AsyncClient, registered_user: User, token_issuer: JwtAccessTokenCodec
) -> None:
    """Return identity fields without exposing the password hash."""
    token = token_issuer.issue(registered_user.id)

    response = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == registered_user.id
    assert body["email"] == registered_user.email
    assert "hashed_password" not in body


async def should_require_access_token_to_read_current_profile(
    client: AsyncClient,
) -> None:
    """Require bearer authentication."""
    response = await client.get("/api/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_current_profile_request_with_invalid_access_token(
    client: AsyncClient,
) -> None:
    """Reject a malformed or incorrectly signed bearer token."""
    response = await client.get(
        "/api/users/me", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_valid_token_when_its_user_no_longer_exists(
    client: AsyncClient, token_issuer: JwtAccessTokenCodec
) -> None:
    """Reload the token subject and reject deleted users."""
    token = token_issuer.issue("deleted-user")

    response = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
