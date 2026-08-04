"""Unit tests for encoding and decoding JWT access tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any, Final

import jwt
import pytest

from app.adapters.jwt_tokens import JwtAccessTokenCodec

SECRET_KEY: Final = "test-secret-key-that-is-long-enough-for-hs256"
ALGORITHM: Final = "HS256"
ACCESS_TOKEN_LIFETIME: Final = timedelta(minutes=30)
SUBJECT: Final = "user-id-1"


@pytest.fixture
def token_issuer() -> JwtAccessTokenCodec:
    """Create a JWT access-token codec configured for unit tests."""
    return JwtAccessTokenCodec(
        secret=SECRET_KEY,
        algorithm=ALGORITHM,
        ttl_seconds=ACCESS_TOKEN_LIFETIME.seconds,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a test access token using the shared key."""
    return jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])


@pytest.mark.unit
def test_should_issue_signed_access_token_for_subject(
    token_issuer: JwtAccessTokenCodec,
) -> None:
    """Issue a signed access token containing the requested subject."""
    token = token_issuer.issue(subject=SUBJECT)

    claims = decode_access_token(token)

    assert claims["sub"] == SUBJECT


@pytest.mark.unit
def test_should_include_required_claims(
    token_issuer: JwtAccessTokenCodec,
) -> None:
    """Include subject, issued-at, and expiration claims in access tokens."""
    before_issue = int(datetime.now(UTC).timestamp())
    token = token_issuer.issue(subject=SUBJECT)
    after_issue = int(datetime.now(UTC).timestamp())

    claims = decode_access_token(token)

    assert claims["sub"] == SUBJECT
    assert before_issue <= claims["iat"] <= after_issue
    assert "exp" in claims


@pytest.mark.unit
def test_should_expire_after_configured_lifetime(
    token_issuer: JwtAccessTokenCodec,
) -> None:
    """Set token expiration according to the configured access-token lifetime."""
    token = token_issuer.issue(subject=SUBJECT)

    claims = decode_access_token(token)

    assert claims["exp"] - claims["iat"] == ACCESS_TOKEN_LIFETIME.seconds
