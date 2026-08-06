"""Routes for authenticating users and issuing access tokens."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AuthServiceDep
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    """Authenticate a user and return an access token."""
    try:
        access_token = await auth_service.login(
            email=payload.email, password=payload.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    return TokenResponse(access_token=access_token)
