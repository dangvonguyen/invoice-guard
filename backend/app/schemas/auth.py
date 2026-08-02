"""Authentication request and response schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Email/password login payload."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """Response body for a successful login."""

    access_token: str
    token_type: str = "bearer"
