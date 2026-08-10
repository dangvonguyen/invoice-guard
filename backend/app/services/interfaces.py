"""Interfaces shared across application boundaries."""

from typing import Protocol
from uuid import UUID

from app.database.models import Invoice, User


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


class InvoiceValidator(Protocol):
    def validate(
        self,
        *,
        filename: str,
        content_type: str,
        size: int,
    ) -> None:
        """Validate uploaded invoice metadata and content."""
        ...


class RateLimiter(Protocol):
    async def allow(self, owner_id: UUID) -> bool:
        """Return whether the owner may perform another upload."""
        ...


class InvoiceRepository(Protocol):
    async def create_pending(
        self,
        *,
        owner_id: UUID,
        storage_key: str,
        original_filename: str,
    ) -> Invoice:
        """Reserve a pending invoice and return its identity."""
        ...


class StorageClient(Protocol):
    def generate_key(self) -> str:
        """Generate an opaque key for invoice storage."""
        ...

    async def save(self, *, key: str, content: bytes) -> None:
        """Persist invoice content under its opaque key."""
        ...
