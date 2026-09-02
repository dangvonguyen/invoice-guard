"""Claim submission service.

The attachment is written to object storage before the claim row is
created, and no row is written if that storage write fails.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.core.rate_limit import RateLimiter
from app.core.storage import StorageClient
from app.database.models.claim import (
    Claim,
    ClaimEntryMethod,
    ClaimLineItem,
    LineItemSource,
)
from app.database.repositories.claim import ClaimRepository
from app.schemas.claim import ClaimSubmissionRequest
from app.services.upload.validation import UploadValidator


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
        request: ClaimSubmissionRequest,
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

        await self._rate_limiter.allow(key=owner_id, scope=self._rate_limit_scope)

        key = self._storage.generate_key()
        await self._storage.save(key=key, content=content)

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
            tax_amount=request.tax_amount,
            original_total_amount=request.total_amount,
            entry_method=ClaimEntryMethod.MANUAL,
            certified_at=self._clock(),
            attachment_key=key,
            attachment_filename=filename or "",
            attachment_content_type=content_type or "",
            attachment_bytes=content_length or len(content),
            line_items=[
                ClaimLineItem(
                    position=position,
                    description=item.description,
                    amount=item.amount,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    source=LineItemSource.EMPLOYEE,
                )
                for position, item in enumerate(request.line_items, start=1)
            ],
        )
        return await self._claim_repo.create(claim)
