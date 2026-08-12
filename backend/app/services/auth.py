"""Authentication service implementations."""

from app.core.logging import bind_user_id
from app.core.security import JwtAccessTokenCodec, PasswordHasher
from app.database.repositories import UserRepository


class InvalidCredentialsError(Exception):
    """Raised when a user provides invalid credentials."""


class AuthService:
    """Authentication service that handles user login and access token generation."""

    def __init__(
        self,
        users: UserRepository,
        password_verifier: PasswordHasher,
        access_token_issuer: JwtAccessTokenCodec,
    ) -> None:
        """Initialize the service with required dependencies."""
        self._users = users
        self._password_verifier = password_verifier
        self._access_token_issuer = access_token_issuer

    async def login(self, email: str, password: str) -> str:
        """Authenticate a user and return an encoded access token.

        Raises:
            InvalidCredentialError: If the email is unknown or the password
                does not match the stored password hash.
        """
        user = await self._users.get_by_email(email)
        if not user:
            await self._password_verifier.verify_dummy(password)
            raise InvalidCredentialsError()
        if not await self._password_verifier.verify(password, user.hashed_password):
            raise InvalidCredentialsError()

        # Associate logs with an account after its credentials are verified
        bind_user_id(str(user.id))

        return self._access_token_issuer.issue(str(user.id))
