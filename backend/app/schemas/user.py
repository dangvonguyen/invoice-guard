from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    """Shared user attributes."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    email: str


class UserCreate(UserBase):
    """User attributes required when creating a user."""

    id: str
    hashed_password: str


class User(UserCreate):
    """Fully populated user returned by persistence operations."""

    created_at: datetime
    updated_at: datetime


class CurrentUserResponse(BaseModel):
    """Response for users getting their own user data."""

    id: str
    email: str
