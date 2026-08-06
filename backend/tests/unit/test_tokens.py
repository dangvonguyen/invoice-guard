"""Specify JWT access-token encoding and validation behavior."""

from datetime import UTC, datetime, timedelta
from typing import Any, Final

import jwt
import pytest

from app.core.security.tokens import JwtAccessTokenCodec

pytestmark = pytest.mark.unit

SECRET_KEY: Final = "test-secret-key-that-is-long-enough-for-hs256"
ALGORITHM: Final = "HS256"
ACCESS_TOKEN_LIFETIME: Final = timedelta(minutes=30)
SUBJECT: Final = "user-id-1"


@pytest.fixture
def access_token_codec() -> JwtAccessTokenCodec:
    """Create a JWT access-token codec configured for unit tests."""
    return JwtAccessTokenCodec(
        secret=SECRET_KEY,
        algorithm=ALGORITHM,
        ttl_seconds=ACCESS_TOKEN_LIFETIME.seconds,
    )


def decode_claims(token: str) -> dict[str, Any]:
    """Decode and validate a test access token using the shared key."""
    return jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])


def should_issue_signed_access_token_for_subject(
    access_token_codec: JwtAccessTokenCodec,
) -> None:
    """Issue a signed access token containing the requested subject."""
    token = access_token_codec.issue(subject=SUBJECT)

    claims = decode_claims(token)

    assert claims["sub"] == SUBJECT


def should_include_required_access_token_claims(
    access_token_codec: JwtAccessTokenCodec,
) -> None:
    """Include subject, issued-at, and expiration claims in access tokens."""
    before_issue = int(datetime.now(UTC).timestamp())
    token = access_token_codec.issue(subject=SUBJECT)
    after_issue = int(datetime.now(UTC).timestamp())

    claims = decode_claims(token)

    assert claims["sub"] == SUBJECT
    assert before_issue <= claims["iat"] <= after_issue
    assert "exp" in claims


def should_expire_access_token_after_configured_lifetime(
    access_token_codec: JwtAccessTokenCodec,
) -> None:
    """Set token expiration according to the configured access-token lifetime."""
    token = access_token_codec.issue(subject=SUBJECT)

    claims = decode_claims(token)

    assert claims["exp"] - claims["iat"] == ACCESS_TOKEN_LIFETIME.seconds


def should_decode_subject_from_valid_access_token(
    access_token_codec: JwtAccessTokenCodec,
) -> None:
    """Validate a token and return its subject."""
    token = access_token_codec.issue(subject=SUBJECT)

    assert access_token_codec.decode(token) == SUBJECT


def should_reject_access_token_with_tampered_signature(
    access_token_codec: JwtAccessTokenCodec,
) -> None:
    """Reject a token whose signature no longer matches its payload."""
    token = access_token_codec.issue(subject=SUBJECT)
    header, payload, signature = token.split(".")
    replacement = "a" if signature[0] != "a" else "b"
    tampered_token = f"{header}.{payload}.{replacement}{signature[1:]}"

    with pytest.raises(ValueError, match="Invalid access token"):
        access_token_codec.decode(tampered_token)
