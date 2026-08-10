"""Define reusable dependencies for API routes."""

from pathlib import Path
from typing import Annotated, Never
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, unwrap_secret
from app.core.logging import bind_user_id
from app.core.rate_limit import RateLimiter, RedisRateLimiter
from app.core.redis import get_redis
from app.core.security import JwtAccessTokenCodec, PasswordHasher
from app.core.storage import LocalStorageClient, StorageClient
from app.database.models.user import User
from app.database.repositories.invoice import InvoiceRepository as DbInvoiceRepository
from app.database.repositories.user import UserRepository as DbUserRepository
from app.database.session import get_session, get_session_manual
from app.services.auth import AuthService
from app.services.interfaces import (
    InvoiceRepository,
    UserRepository,
)
from app.services.invoice_intake import InvoiceIntakeService
from app.services.invoice_mime_validator import InvoiceMimeValidator

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionManualDep = Annotated[AsyncSession, Depends(get_session_manual)]
RedisDep = Annotated[Redis, Depends(get_redis)]


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


bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
]


def raise_unauthorized() -> Never:
    """Raise the generic authentication failure used by protected routes."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: BearerCredentialsDep,
    users: UserRepositoryDep,
    access_token_codec: AccessTokenCodecDep,
) -> User:
    """Validate a bearer token and reload its user from the database."""
    if credentials is None:
        raise_unauthorized()
    try:
        user_id = UUID(access_token_codec.decode(credentials.credentials))
    except ValueError:
        raise_unauthorized()

    user = await users.get_by_id(user_id)
    if user is None:
        raise_unauthorized()

    bind_user_id(str(user.id))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# --------------------------- Invoice Intake -----------------------------
#
# get_invoice_repository is deliberately bound to SessionManualDep, not
# SessionDep. The pending row must survive a later storage failure within
# the same request, which the ambient auto-commit-on-success session
# (SessionDep) would roll back.


def get_invoice_repository(session: SessionManualDep) -> InvoiceRepository:
    """Create an invoice repository configured with a manually-controlled session."""
    return DbInvoiceRepository(session=session)


InvoiceRepositoryDep = Annotated[InvoiceRepository, Depends(get_invoice_repository)]


def get_invoice_mime_validator() -> InvoiceMimeValidator:
    """Create the invoice upload validator from configured limits."""
    return InvoiceMimeValidator()


InvoiceMimeValidatorDep = Annotated[
    InvoiceMimeValidator, Depends(get_invoice_mime_validator)
]


def get_upload_rate_limiter(redis: RedisDep) -> RateLimiter:
    """Create the Redis-backed upload rate limiter from configured limits."""
    settings = get_settings()
    return RedisRateLimiter(
        redis=redis,
        limit=settings.UPLOAD_RATE_LIMIT,
        window_seconds=settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
    )


UploadRateLimiterDep = Annotated[RateLimiter, Depends(get_upload_rate_limiter)]


def get_storage_client() -> StorageClient:
    """Create the object storage client - Local disk."""
    settings = get_settings()
    return LocalStorageClient(base_path=Path(settings.STORAGE_LOCAL_PATH))


StorageClientDep = Annotated[StorageClient, Depends(get_storage_client)]


def get_invoice_intake_service(
    validator: InvoiceMimeValidatorDep,
    rate_limiter: UploadRateLimiterDep,
    invoices: InvoiceRepositoryDep,
    storage: StorageClientDep,
) -> InvoiceIntakeService:
    """Create the invoice intake service from its injected dependencies."""
    return InvoiceIntakeService(
        validator=validator,
        rate_limiter=rate_limiter,
        invoices=invoices,
        storage=storage,
    )


InvoiceIntakeServiceDep = Annotated[
    InvoiceIntakeService, Depends(get_invoice_intake_service)
]
