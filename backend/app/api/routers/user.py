from fastapi import APIRouter

from app.models.user import User
from app.schemas.user import CurrentUserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_user_me() -> User:
    """Get the current user's data."""
    raise NotImplementedError
