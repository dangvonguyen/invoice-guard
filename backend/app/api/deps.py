"""Define reusable dependencies for API routes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.jwt_tokens import JwtAccessTokenCodec
from app.adapters.password_hasher import PasswordHasher
from app.config.settings import get_settings, unwrap_secret
from app.database.db import get_session, get_session_manual
from app.ports import UserRepository
from app.repositories.user import UserRepository as DbUserRepository
from app.service.auth import AuthService

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionManualDep = Annotated[AsyncSession, Depends(get_session_manual)]


def get_user_repository(session: SessionDep) -> UserRepository:
    """Create a user repository configured with the database session."""
    return DbUserRepository(session=session)


def get_password_hasher() -> PasswordHasher:
    """Create the password verifier."""
    return PasswordHasher()


def get_access_token_codec() -> JwtAccessTokenCodec:
    """Create a token codec configured with the application settings."""
    settings = get_settings()

    return JwtAccessTokenCodec(
        secret=unwrap_secret(settings.JWT_SECRET_KEY),
        ttl_seconds=settings.JWT_ACCESS_TOKEN_MINUTES * 60,
    )


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
AccessTokenCodecDep = Annotated[JwtAccessTokenCodec, Depends(get_access_token_codec)]


def get_auth_service(
    users: UserRepositoryDep,
    password_verifier: PasswordHasherDep,
    access_token_issuer: AccessTokenCodecDep,
) -> AuthService:
    """Create an authentication service from its injected dependencies."""
    return AuthService(
        users=users,
        password_verifier=password_verifier,
        access_token_issuer=access_token_issuer,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
