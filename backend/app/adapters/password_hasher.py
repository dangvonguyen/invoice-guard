"""Verify passwords against securely stored hashes."""

import asyncio

from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.base import HasherProtocol

_DUMMY_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$4vnjKqM2CxkKkWmlv7IqLw$5RweWEJuM//guLnmoY6uQofz9fFKECzzhKtF+IcxACQ"


class PasswordHasher:
    """Adapt a password hashing implementation for authentication."""

    def __init__(self, hasher: HasherProtocol | None = None) -> None:
        """Initialize with the given hasher or a default Argon2 hasher."""
        self._hasher = hasher or Argon2Hasher()

    def hash(self, password: str) -> str:
        """Return a secure hash of a plaintext password."""
        return self._hasher.hash(password)

    async def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return whether a plain-text password matches a stored hash."""
        return await asyncio.to_thread(
            self._hasher.verify, plain_password, hashed_password
        )

    async def verify_dummy(self, plain_password: str) -> None:
        """Perform password verification when no stored user hash exists."""
        await self.verify(plain_password, _DUMMY_PASSWORD_HASH)
