"""Unit tests for password hash verification."""

from unittest.mock import Mock

import pytest
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.base import HasherProtocol

from app.adapters.password_hasher import PasswordHasher


@pytest.fixture
def hasher() -> Argon2Hasher:
    """Provide an Argon2 hasher for deterministic adapter tests."""
    return Argon2Hasher()


@pytest.mark.unit
def test_should_delegate_password_hashing() -> None:
    """Return the hash produced by the configured hashing implementation."""
    hasher = Mock(spec=HasherProtocol)
    hasher.hash.return_value = "hashed-password"

    result = PasswordHasher(hasher=hasher).hash("plain-password")

    hasher.hash.assert_called_once_with("plain-password")
    assert result == "hashed-password"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_accept_matching_password(hasher: Argon2Hasher) -> None:
    """Accept a password that matches its stored hash."""
    hashed = hasher.hash("correct-password")
    assert (
        await PasswordHasher(hasher=hasher).verify("correct-password", hashed) is True
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_reject_non_matching_password(hasher: Argon2Hasher) -> None:
    """Reject a password that does not match the stored hash."""
    hashed = hasher.hash("correct-password")
    assert await PasswordHasher(hasher=hasher).verify("wrong-password", hashed) is False
