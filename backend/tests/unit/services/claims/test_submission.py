"""Specify how the claim submission service coordinates its collaborators."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.database.models.claim import Claim
from app.schemas.claim import ClaimCreateRequest
from app.services.claims.submission import (
    ClaimSubmissionRateLimitExceededError,
    ClaimSubmissionService,
)
from app.services.upload.validation import UnsupportedMediaTypeError
from tests.support.constants import VALID_SUBMISSION_PAYLOAD

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
STORAGE_KEY = "20000000-0000-0000-0000-000000000001"
FILENAME = "figma-invoice.pdf"
CONTENT_TYPE = "application/pdf"
PDF_CONTENT = b"%PDF-1.4\nfigma invoice\n"
RATE_LIMIT_SCOPE = "claim-submission"
FIXED_NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def build_request(**overrides: Any) -> ClaimCreateRequest:
    """The canonical valid submission request, with optional field overrides."""
    payload: dict[str, Any] = {**VALID_SUBMISSION_PAYLOAD, **overrides}
    return ClaimCreateRequest.model_validate(payload)


@dataclass(frozen=True)
class SubmissionContext:
    """The service under test and its mocked collaborators."""

    service: ClaimSubmissionService
    validator: Mock
    rate_limiter: AsyncMock
    claim_repo: AsyncMock
    storage: AsyncMock


@pytest.fixture
def context() -> SubmissionContext:
    """Wire the submission service with mocks for every collaborator."""
    validator = Mock()
    rate_limiter = AsyncMock()
    rate_limiter.allow.return_value = True
    claim_repo = AsyncMock()
    claim_repo.create.side_effect = lambda claim: claim
    storage = AsyncMock()
    storage.generate_key = Mock(return_value=STORAGE_KEY)
    service = ClaimSubmissionService(
        validator=validator,
        rate_limiter=rate_limiter,
        claim_repo=claim_repo,
        storage=storage,
        clock=lambda: FIXED_NOW,
    )
    return SubmissionContext(service, validator, rate_limiter, claim_repo, storage)


async def submit(context: SubmissionContext, **overrides: Any) -> Claim:
    """Invoke ``submit`` with valid defaults and optional overrides."""
    kwargs: dict[str, Any] = {
        "owner_id": OWNER_ID,
        "request": build_request(),
        "filename": FILENAME,
        "content_type": CONTENT_TYPE,
        "content_length": len(PDF_CONTENT),
        "content": PDF_CONTENT,
    }
    kwargs.update(overrides)
    return await context.service.submit(**kwargs)


async def should_validate_store_then_persist_a_manual_submission(
    context: SubmissionContext,
) -> None:
    """Run validation and the rate check, write the attachment, then persist."""
    await submit(context)

    context.validator.validate.assert_called_once_with(
        filename=FILENAME,
        content_type=CONTENT_TYPE,
        content_length=len(PDF_CONTENT),
        content=PDF_CONTENT,
    )
    context.rate_limiter.allow.assert_awaited_once_with(
        key=OWNER_ID, scope=RATE_LIMIT_SCOPE
    )
    context.storage.save.assert_awaited_once_with(key=STORAGE_KEY, content=PDF_CONTENT)
    context.claim_repo.create.assert_awaited_once()


async def should_write_storage_before_creating_the_row(
    context: SubmissionContext,
) -> None:
    """A submitted claim must never exist without its stored document."""
    call_order: list[str] = []
    context.storage.save.side_effect = lambda **_: call_order.append("save")
    context.claim_repo.create.side_effect = lambda _: call_order.append("create")

    await submit(context)

    assert call_order == ["save", "create"]


async def should_reject_the_submission_when_the_rate_limit_denies_it(
    context: SubmissionContext,
) -> None:
    """Stop before storage or persistence once the quota is spent."""
    context.rate_limiter.allow.return_value = False

    with pytest.raises(ClaimSubmissionRateLimitExceededError):
        await submit(context)

    context.validator.validate.assert_called_once()
    context.storage.save.assert_not_awaited()
    context.claim_repo.create.assert_not_awaited()


async def should_propagate_validation_failures_without_touching_anything_else(
    context: SubmissionContext,
) -> None:
    """Never rate-limit, store, or persist an attachment that fails validation."""
    context.validator.validate.side_effect = UnsupportedMediaTypeError(
        "image/jpeg is not yet supported"
    )

    with pytest.raises(UnsupportedMediaTypeError):
        await submit(context)

    context.rate_limiter.allow.assert_not_awaited()
    context.storage.save.assert_not_awaited()
    context.claim_repo.create.assert_not_awaited()
