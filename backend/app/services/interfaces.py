"""Interfaces shared across application boundaries."""

from typing import Protocol
from uuid import UUID

from app.database.models.user import User


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None:
        """Return the user associated with an email address, if one exists."""
        ...

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user associated with an ID, if one exists."""
        ...


class PasswordVerifier(Protocol):
    async def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return whether a plain-text password matches its stored hash."""
        ...

    async def verify_dummy(self, plain_password: str) -> None:
        """Perform password verification without a stored user hash."""
        ...


class AccessTokenIssuer(Protocol):
    def issue(self, subject: str) -> str:
        """Issue an access token identifying the supplied subject."""
        ...
