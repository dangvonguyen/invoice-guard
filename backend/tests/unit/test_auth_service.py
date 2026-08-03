"""Unit tests for the authentication service."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.ports import AccessTokenIssuer, PasswordVerifier, User, UserRepository
from app.service.auth import AuthService, InvalidCredentialsError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_issue_access_token_for_valid_credentials() -> None:
    """Issue an access token when the supplied credentials are valid."""
    user = User(id="user-1", email="user@example.com", hashed_password="hashed")
    users = AsyncMock(spec=UserRepository)
    users.get_by_email.return_value = user
    password_verifier = AsyncMock(spec=PasswordVerifier)
    password_verifier.verify.return_value = True
    access_token_issuer = Mock(spec=AccessTokenIssuer)
    access_token_issuer.issue.return_value = "signed.jwt.token"

    service = AuthService(
        users=users,
        password_verifier=password_verifier,
        access_token_issuer=access_token_issuer,
    )
    token = await service.login(email="user@example.com", password="correct-password")

    assert token == "signed.jwt.token"
    users.get_by_email.assert_awaited_once_with("user@example.com")
    password_verifier.verify.assert_awaited_once_with("correct-password", "hashed")
    access_token_issuer.issue.assert_called_once_with("user-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_reject_login_when_user_does_not_exist() -> None:
    """Reject login without verifying a password when the user is unknown."""
    users = AsyncMock(spec=UserRepository)
    users.get_by_email.return_value = None
    password_verifier = AsyncMock(spec=PasswordVerifier)
    access_token_issuer = Mock(spec=AccessTokenIssuer)

    service = AuthService(
        users=users,
        password_verifier=password_verifier,
        access_token_issuer=access_token_issuer,
    )

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="unknown@example.com", password="whatever")
    password_verifier.assert_not_called()
    access_token_issuer.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_reject_login_when_password_is_wrong() -> None:
    """Reject login and avoid issuing a token when the password is invalid."""
    user = User(id="user-1", email="user@example.com", hashed_password="hashed")
    users = AsyncMock(spec=UserRepository)
    users.get_by_email.return_value = user
    password_verifier = AsyncMock(spec=PasswordVerifier)
    password_verifier.verify.return_value = False
    access_token_issuer = Mock(spec=AccessTokenIssuer)

    service = AuthService(
        users=users,
        password_verifier=password_verifier,
        access_token_issuer=access_token_issuer,
    )

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="user@example.com", password="wrong-password")
    access_token_issuer.assert_not_called()
