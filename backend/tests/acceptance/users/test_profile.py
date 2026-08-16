"""Acceptance scenarios for retrieving profiles with bearer authentication."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.deps import get_access_token_codec
from app.database.models.user import User

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


async def should_return_authenticated_users_profile_without_password_hash(
    client: AsyncClient, employee: User, employee_headers: dict[str, str]
) -> None:
    """Return identity fields without exposing the password hash."""
    response = await client.get("/users/me", headers=employee_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == str(employee.id)
    assert body["email"] == employee.email
    assert body["name"] == employee.name
    assert body["role"] == employee.role
    assert "hashed_password" not in body


async def should_require_access_token_to_read_current_profile(
    client: AsyncClient,
) -> None:
    """Require bearer authentication."""
    response = await client.get("/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_current_profile_request_with_invalid_access_token(
    client: AsyncClient,
) -> None:
    """Reject a malformed or incorrectly signed bearer token."""
    response = await client.get(
        "/users/me", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_valid_token_when_its_user_no_longer_exists(
    client: AsyncClient,
) -> None:
    """Reload the token subject and reject deleted users."""
    token = get_access_token_codec().issue("deleted-user")

    response = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
