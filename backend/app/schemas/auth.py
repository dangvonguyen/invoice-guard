"""Authentication request and response schemas."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Response body for a successful login."""

    access_token: str
    token_type: str = "bearer"
