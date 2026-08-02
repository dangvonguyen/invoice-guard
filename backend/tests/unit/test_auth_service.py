"""Unit tests for the authentication service."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.ports import User
from app.service.auth import AuthService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_issue_access_token_for_valid_credentials() -> None:
    """Issue an access token when the supplied credentials are valid."""
    user = User(id="user-1", email="user@example.com", hashed_password="hashed")
    users = AsyncMock()
    users.get_by_email.return_value = user
    password_verifier = AsyncMock()
    password_verifier.verify.return_value = True
    access_token_encoder = Mock()
    access_token_encoder.encode.return_value = "signed.jwt.token"

    service = AuthService(
        users=users,
        password_verifier=password_verifier,
        access_token_encoder=access_token_encoder,
    )
    token = await service.login(email="user@example.com", password="correct-password")

    assert token == "signed.jwt.token"
    users.get_by_email.assert_awaited_once_with("user@example.com")
    password_verifier.verify.assert_awaited_once_with("correct-password", "hashed")
    access_token_encoder.encode.assert_called_once_with("user-1")
