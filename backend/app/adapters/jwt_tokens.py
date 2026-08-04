"""Issue JSON Web Tokens for authenticated users."""

from datetime import UTC, datetime, timedelta

import jwt


class JwtAccessTokenCodec:
    """Encode short-lived JWT access tokens."""

    def __init__(
        self, secret: str, algorithm: str = "HS256", ttl_seconds: int = 1800
    ) -> None:
        """Configure token signing and lifetime settings."""
        self._secret = secret
        self._algorithm = algorithm
        self._ttl_seconds = ttl_seconds

    def issue(self, subject: str) -> str:
        """Issue a signed access token for the given subject."""
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self._ttl_seconds)
        payload = {
            "sub": subject,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, key=self._secret, algorithm=self._algorithm)
