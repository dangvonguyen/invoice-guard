"""Specify how the authentication service coordinates login collaborators."""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.database.models.user import User
from app.services.auth import AuthService, InvalidCredentialsError
from app.services.interfaces import AccessTokenIssuer, PasswordVerifier, UserRepository

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

KNOWN_EMAIL = "user@example.com"
KNOWN_PASSWORD = "correct-password"
PASSWORD_HASH = "stored-password-hash"
ACCESS_TOKEN = "signed.jwt.token"


@dataclass(frozen=True)
class AuthenticationContext:
    """Expose the service and collaborator roles used by each scenario."""

    service: AuthService
    users: AsyncMock
    password_verifier: AsyncMock
    access_token_issuer: Mock


@pytest.fixture
def registered_user() -> User:
    """Return the account associated with the known login email."""
    timestamp = datetime(2000, 1, 1, tzinfo=UTC)
    return User(
        id="user-1",
        email=KNOWN_EMAIL,
        hashed_password=PASSWORD_HASH,
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.fixture
def auth() -> AuthenticationContext:
    """Build the service with mocks for the roles it coordinates."""
    users = AsyncMock(spec=UserRepository)
    password_verifier = AsyncMock(spec=PasswordVerifier)
    access_token_issuer = Mock(spec=AccessTokenIssuer)
    service = AuthService(
        users=users,
        password_verifier=password_verifier,
        access_token_issuer=access_token_issuer,
    )
    return AuthenticationContext(
        service=service,
        users=users,
        password_verifier=password_verifier,
        access_token_issuer=access_token_issuer,
    )


async def should_issue_access_token_for_valid_credentials(
    auth: AuthenticationContext, registered_user: User
) -> None:
    """Issue an access token when the supplied credentials are valid."""
    auth.users.get_by_email.return_value = registered_user
    auth.password_verifier.verify.return_value = True
    auth.access_token_issuer.issue.return_value = ACCESS_TOKEN

    token = await auth.service.login(KNOWN_EMAIL, KNOWN_PASSWORD)

    assert token == ACCESS_TOKEN
    auth.users.get_by_email.assert_awaited_once_with(KNOWN_EMAIL)
    auth.password_verifier.verify.assert_awaited_once_with(
        KNOWN_PASSWORD, PASSWORD_HASH
    )
    auth.access_token_issuer.issue.assert_called_once_with(registered_user.id)


async def should_reject_login_when_email_is_not_registered(
    auth: AuthenticationContext,
) -> None:
    """Reject login when the user is unknown."""
    auth.users.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        await auth.service.login("unknown@example.com", "unknown-password")

    auth.access_token_issuer.issue.assert_not_called()


async def should_verify_dummy_hash_when_email_is_not_registered(
    auth: AuthenticationContext,
) -> None:
    """Perform password verification before rejecting an unknown user."""
    auth.users.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        await auth.service.login("unknown@example.com", "unknown-password")

    auth.password_verifier.verify_dummy.assert_awaited_once_with("unknown-password")
    auth.password_verifier.verify.assert_not_awaited()


async def should_reject_login_when_password_does_not_match(
    auth: AuthenticationContext, registered_user: User
) -> None:
    """Reject login and avoid issuing a token when the password is invalid."""
    auth.users.get_by_email.return_value = registered_user
    auth.password_verifier.verify.return_value = False

    with pytest.raises(InvalidCredentialsError):
        await auth.service.login(KNOWN_EMAIL, "wrong-password")

    auth.password_verifier.verify.assert_awaited_once_with(
        "wrong-password", PASSWORD_HASH
    )
    auth.access_token_issuer.issue.assert_not_called()
