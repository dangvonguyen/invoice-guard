"""Routes for authenticating users and issuing access tokens."""

from fastapi import APIRouter

from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest) -> TokenResponse:
    """Authenticate a user and return an access token."""
    raise NotImplementedError
