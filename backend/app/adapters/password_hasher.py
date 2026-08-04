"""Verify passwords against securely stored hashes."""

import asyncio

from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.base import HasherProtocol


class PasswordHasher:
    """Adapt a password hashing implementation for authentication."""

    def __init__(self, hasher: HasherProtocol | None = None) -> None:
        """Initialize with the given hasher or a default Argon2 hasher."""
        self._hasher = hasher or Argon2Hasher()

    async def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return whether a plain-text password matches a stored hash."""
        return await asyncio.to_thread(
            self._hasher.verify, plain_password, hashed_password
        )
