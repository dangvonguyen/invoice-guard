"""Dependencies for claim submission."""

from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter, RedisRateLimiter
from app.database.repositories.claim import ClaimRepository
from app.services.claims.submission import ClaimSubmissionService
from app.services.upload.validation import UploadValidator

from .invoices import StorageClientDep
from .sessions import RedisDep, SessionManualDep


# SessionManualDep so the claim row's transaction is owned by the repository,
# committed only after the attachment is safely in storage.
def get_claim_repository(session: SessionManualDep) -> ClaimRepository:
    """Create a claim repository configured with a manually-controlled session."""
    return ClaimRepository(session=session)


ClaimRepositoryDep = Annotated[ClaimRepository, Depends(get_claim_repository)]


def get_claim_upload_validator() -> UploadValidator:
    """Reuse the configured upload contract for claim attachments."""
    return UploadValidator(max_bytes=get_settings().UPLOAD_MAX_BYTES)


ClaimUploadValidatorDep = Annotated[
    UploadValidator, Depends(get_claim_upload_validator)
]


def get_claim_submission_rate_limiter(redis: RedisDep) -> RateLimiter:
    """Reuse the upload rate-limit budget for claim submissions."""
    settings = get_settings()
    return RedisRateLimiter(
        redis=redis,
        limit=settings.UPLOAD_RATE_LIMIT,
        window_seconds=settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
    )


ClaimSubmissionRateLimiterDep = Annotated[
    RateLimiter, Depends(get_claim_submission_rate_limiter)
]


def get_claim_submission_service(
    validator: ClaimUploadValidatorDep,
    rate_limiter: ClaimSubmissionRateLimiterDep,
    claim_repo: ClaimRepositoryDep,
    storage: StorageClientDep,
) -> ClaimSubmissionService:
    """Create the claim submission service from its injected dependencies."""
    return ClaimSubmissionService(
        validator=validator,
        rate_limiter=rate_limiter,
        claim_repo=claim_repo,
        storage=storage,
    )


ClaimSubmissionServiceDep = Annotated[
    ClaimSubmissionService, Depends(get_claim_submission_service)
]
