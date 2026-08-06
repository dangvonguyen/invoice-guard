"""Specify password hashing and verification behavior."""

from unittest.mock import Mock

import pytest
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.base import HasherProtocol

from app.adapters.password_hasher import PasswordHasher

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> Argon2Hasher:
    """Provide an Argon2 hasher for deterministic adapter tests."""
    return Argon2Hasher()


def should_delegate_password_hashing_to_configured_hasher() -> None:
    """Return the hash produced by the configured hashing implementation."""
    hasher = Mock(spec=HasherProtocol)
    hasher.hash.return_value = "hashed-password"

    result = PasswordHasher(hasher=hasher).hash("plain-password")

    hasher.hash.assert_called_once_with("plain-password")
    assert result == "hashed-password"


@pytest.mark.asyncio
async def should_accept_password_matching_stored_hash(hasher: Argon2Hasher) -> None:
    """Accept a password that matches its stored hash."""
    hashed = hasher.hash("correct-password")
    assert (
        await PasswordHasher(hasher=hasher).verify("correct-password", hashed) is True
    )


@pytest.mark.asyncio
async def should_reject_password_not_matching_stored_hash(
    hasher: Argon2Hasher,
) -> None:
    """Reject a password that does not match the stored hash."""
    hashed = hasher.hash("correct-password")
    assert await PasswordHasher(hasher=hasher).verify("wrong-password", hashed) is False
