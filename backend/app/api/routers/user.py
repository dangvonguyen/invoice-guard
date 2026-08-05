from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.models.user import User
from app.schemas.user import CurrentUserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_user_me(current_user: CurrentUserDep) -> User:
    """Get the current user's data."""
    return CurrentUserResponse(id=current_user.id, email=current_user.email)
