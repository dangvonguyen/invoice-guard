"""API endpoints for user account operations."""

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import CurrentUserResponse, User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_user_me(current_user: CurrentUser) -> User:
    """Get the current user's data."""
    return current_user
