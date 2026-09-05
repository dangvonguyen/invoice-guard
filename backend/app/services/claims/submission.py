"""Claim submission service.

The attachment is written to object storage before the claim row is
created, and no row is written if that storage write fails.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import DomainError
from app.core.rate_limit import RateLimiter
from app.core.storage import StorageClient, StorageWriteError
from app.database.models.claim import Claim
from app.database.repositories.claim import ClaimRepository
from app.schemas.claim import ClaimCreateRequest
from app.services.upload.intake import UploadStorageUnavailableError
from app.services.upload.validation import UploadValidator


class ClaimSubmissionRateLimitExceededError(DomainError):
    """Raised when an employee exceeds their claim-submission rate limit."""

    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ClaimSubmissionService:
    """Coordinate validation, storage, and persistence of a claim submission."""

    def __init__(
        self,
        validator: UploadValidator,
        rate_limiter: RateLimiter,
        claim_repo: ClaimRepository,
        storage: StorageClient,
        clock: Callable[[], datetime] = _utcnow,
        rate_limit_scope: str = "claim-submission",
    ) -> None:
        self._validator = validator
        self._rate_limiter = rate_limiter
        self._claim_repo = claim_repo
        self._storage = storage
        self._clock = clock
        self._rate_limit_scope = rate_limit_scope

    async def submit(
        self,
        *,
        owner_id: UUID,
        request: ClaimCreateRequest,
        filename: str | None,
        content_type: str | None,
        content_length: int | None,
        content: bytes,
    ) -> Claim:
        """Validate, store the attachment, then persist the submitted claim."""
        self._validator.validate(
            filename=filename,
            content_type=content_type,
            content_length=content_length,
            content=content,
        )

        if not await self._rate_limiter.allow(
            key=owner_id, scope=self._rate_limit_scope
        ):
            raise ClaimSubmissionRateLimitExceededError(
                f"claim submission rate limit exceeded for {owner_id}"
            )

        key = self._storage.generate_key()
        try:
            await self._storage.save(key=key, content=content)
        except StorageWriteError as exc:
            raise UploadStorageUnavailableError(
                f"storage failed for claim submission by {owner_id}"
            ) from exc

        claim = Claim(
            owner_id=owner_id,
            expense_title=request.expense_title,
            business_purpose=request.business_purpose,
            category=request.category,
            cost_center=request.cost_center,
            vendor=request.vendor,
            invoice_number=request.invoice_number,
            invoice_date=request.invoice_date,
            total_amount=request.total_amount,
            currency=request.currency,
            original_total_amount=request.total_amount,
            certified_at=self._clock(),
            attachment_key=key,
            attachment_filename=filename or "",
            attachment_content_type=content_type or "",
            attachment_bytes=content_length or len(content),
        )
        return await self._claim_repo.create(claim)
