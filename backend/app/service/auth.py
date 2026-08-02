"""Authentication service implementations."""

from app.ports import AccessTokenEncoder, PasswordVerifier, UserRepository


class InvalidCredentialsError(Exception):
    """Raised when a user provides invalid credentials."""


class AuthService:
    """Authentication service that handles user login and access token generation."""

    def __init__(
        self,
        users: UserRepository,
        password_verifier: PasswordVerifier,
        access_token_encoder: AccessTokenEncoder,
    ) -> None:
        """Initialize the service with required dependencies."""
        self._users = users
        self._password_verifier = password_verifier
        self._access_token_encoder = access_token_encoder

    async def login(self, email: str, password: str) -> str:
        """Authenticate a user and return an encoded access token.

        Raises:
            InvalidCredentialError: If the email is unknown.
        """
        user = await self._users.get_by_email(email)
        if not user:
            raise InvalidCredentialsError()
        await self._password_verifier.verify(password, user.hashed_password)
        return self._access_token_encoder.encode(user.id)
