"""Acceptance scenarios for issuing access tokens from login credentials."""

from typing import Any

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import UserModel

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def registered_user(test_db: AsyncSession) -> UserModel:
    """Persist an account with credentials known to the scenarios."""
    user = UserModel(
        id="user-1",
        email="user@example.com",
        hashed_password=Argon2Hasher().hash("secret123"),
    )
    test_db.add(user)
    await test_db.flush()
    return user


async def should_issue_access_token_when_registered_credentials_are_valid(
    client: AsyncClient, registered_user: UserModel
) -> None:
    """Return a bearer token when valid credentials are submitted."""
    response = await client.post(
        "/api/auth/login",
        json={"email": registered_user.email, "password": "secret123"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


async def should_reject_login_when_registered_users_password_is_wrong(
    client: AsyncClient, registered_user: UserModel
) -> None:
    """Reject login attempts with incorrect passwords."""
    response = await client.post(
        "/api/auth/login",
        json={"email": registered_user.email, "password": "wrong-password"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_login_when_email_is_not_registered(
    client: AsyncClient,
) -> None:
    """Reject login attempts for unknown users."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "whatever"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "email": "user@example.com",
        },
        {
            "password": "secret123",
        },
        {
            "email": "",
            "password": "secret123",
        },
        {
            "email": "user@example.com",
            "password": "",
        },
    ],
)
async def should_reject_login_when_required_credentials_are_missing_or_empty(
    client: AsyncClient, payload: dict[str, Any]
) -> None:
    """Ensure rejecting requests with missing or empty fields."""
    response = await client.post("/api/auth/login", json=payload)

    assert response.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
