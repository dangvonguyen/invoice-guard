"""Domain models and interfaces shared across application boundaries."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class User:
    id: str
    email: str
    hashed_password: str


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None:
        """Return the user associated with an email address, if one exists."""
        ...


class PasswordVerifier(Protocol):
    async def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return whether a plain-text password matches its stored hash."""
        ...


class AccessTokenEncoder(Protocol):
    def encode(self, subject: str) -> str:
        """Issue an access token identifying the supplied subject."""
        ...
