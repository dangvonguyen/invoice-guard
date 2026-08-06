"""Validation and transfer schemas for user API data."""

from pydantic import BaseModel, Field

from app.database.models.user import UserRole


class UserLoginRequest(BaseModel):
    """Email/password login payload."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class CurrentUserResponse(BaseModel):
    """Response for users getting their own user data."""

    id: str
    email: str
    name: str
    role: UserRole
