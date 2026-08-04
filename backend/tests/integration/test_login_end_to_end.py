"""Verify login through FastAPI's dependency graph and a real database."""

import pytest
from httpx import AsyncClient
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User as UserModel


@pytest.mark.asyncio
async def test_login_succeeds_end_to_end_against_real_database(
    client: AsyncClient, test_db: AsyncSession
) -> None:
    """Verify that credentials stored in database authenticate through the API."""
    password = "secret123"
    test_db.add(
        UserModel(
            id="persisted-user-1",
            email="persisted@example.com",
            hashed_password=Argon2Hasher().hash(password),
        )
    )
    await test_db.flush()

    response = await client.post(
        "/api/auth/login",
        json={"email": "persisted@example.com", "password": password},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
