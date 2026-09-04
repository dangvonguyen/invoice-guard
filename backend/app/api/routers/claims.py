"""Routes for claim submission."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.deps import ClaimSubmissionServiceDep, CurrentUser
from app.api.openapi import UNAUTHORIZED_RESPONSE
from app.core.config import get_settings
from app.schemas.claim import ClaimCreateRequest, ClaimCreateResponse
from app.schemas.envelope import ResponseEnvelope
from app.services.claims.submission import ClaimSubmissionRateLimitExceededError
from app.services.upload.intake import UploadStorageUnavailableError
from app.services.upload.validation import InvalidUploadError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
    responses=UNAUTHORIZED_RESPONSE,
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_claim(
    current_user: CurrentUser,
    claim_service: ClaimSubmissionServiceDep,
    data: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> ResponseEnvelope[ClaimCreateResponse, None]:
    """Create a claim with its supporting document."""
    content = await file.read(get_settings().UPLOAD_MAX_BYTES + 1)

    request = _parse_claim_request(data)

    try:
        claim = await claim_service.submit(
            owner_id=current_user.id,
            request=request,
            filename=file.filename,
            content_type=file.content_type,
            content_length=len(content),
            content=content,
        )
    except (InvalidUploadError, ClaimSubmissionRateLimitExceededError) as exc:
        _log_rejection(code=exc.code, status_code=exc.status_code)
        raise
    except UploadStorageUnavailableError as exc:
        _log_rejection(code="STORAGE_UNAVAILABLE", status_code=503)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage is temporarily unavailable.",
        ) from exc

    logger.info(
        "Claim created",
        extra={
            "event": "claim.creation.accepted",
            "context": {
                "status_code": status.HTTP_201_CREATED,
            },
        },
    )

    return ResponseEnvelope(data=ClaimCreateResponse.model_validate(claim))


def _parse_claim_request(data: str) -> ClaimCreateRequest:
    try:
        return ClaimCreateRequest.model_validate_json(data)
    except ValidationError as exc:
        _log_rejection(
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
        raise RequestValidationError(exc.errors()) from exc


def _log_rejection(*, code: str, status_code: int, **context: object) -> None:
    logger.warning(
        "Claim submission rejected",
        extra={
            "event": "claim.submission.rejected",
            "context": {"code": code, "status_code": status_code, **context},
        },
    )
