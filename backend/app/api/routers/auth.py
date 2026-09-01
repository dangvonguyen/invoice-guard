"""Routes for authenticating users and issuing access tokens."""

from fastapi import APIRouter

from app.api.deps import AuthServiceDep
from app.schemas.auth import TokenResponse
from app.schemas.user import UserLoginRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(
    payload: UserLoginRequest, auth_service: AuthServiceDep
) -> TokenResponse:
    """Authenticate a user and return an access token."""
    access_token = await auth_service.login(
        email=payload.email,
        password=payload.password,
    )
    return TokenResponse(access_token=access_token)
