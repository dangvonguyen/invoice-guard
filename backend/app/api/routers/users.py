"""API endpoints for user account operations."""

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.api.openapi import UNAUTHORIZED_RESPONSE
from app.schemas.envelope import ResponseEnvelope
from app.schemas.user import CurrentUserResponse

router = APIRouter(prefix="/users", tags=["Users"], responses=UNAUTHORIZED_RESPONSE)


@router.get("/me")
async def get_user_me(
    current_user: CurrentUser,
) -> ResponseEnvelope[CurrentUserResponse, None]:
    """Get the current user's data."""
    return ResponseEnvelope(data=CurrentUserResponse.model_validate(current_user))
