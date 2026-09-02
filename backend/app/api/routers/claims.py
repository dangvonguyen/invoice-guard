"""Routes for claim submission."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.deps import ClaimSubmissionServiceDep, CurrentUser
from app.api.openapi import UNAUTHORIZED_RESPONSE
from app.core.config import get_settings
from app.schemas.claim import ClaimSubmissionRequest, ClaimSubmissionResponse
from app.schemas.envelope import ResponseEnvelope
from app.services.claims.submission import ClaimSubmissionRateLimitExceededError
from app.services.upload.intake import UploadStorageUnavailableError
from app.services.upload.validation import InvalidUploadError

router = APIRouter(prefix="/claims", tags=["Claims"])
logger = logging.getLogger(__name__)


@router.post("", status_code=status.HTTP_201_CREATED, responses=UNAUTHORIZED_RESPONSE)
async def submit_claim(
    current_user: CurrentUser,
    submission: ClaimSubmissionServiceDep,
    data: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> ResponseEnvelope[ClaimSubmissionResponse, None]:
    """Submit a claim with associated document."""
    content = await file.read(get_settings().UPLOAD_MAX_BYTES + 1)

    try:
        request = ClaimSubmissionRequest.model_validate_json(data)
    except ValidationError as exc:
        _log_rejection(code="VALIDATION_ERROR", status_code=422)
        raise RequestValidationError(exc.errors()) from exc

    try:
        claim = await submission.submit(
            owner_id=current_user.id,
            request=request,
            filename=file.filename,
            content_type=file.content_type,
            content_length=len(content),
            content=content,
        )
    except ClaimSubmissionRateLimitExceededError as exc:
        _log_rejection(code=exc.code, status_code=exc.status_code)
        raise
    except InvalidUploadError as exc:
        _log_rejection(code=exc.code, status_code=exc.status_code)
        raise
    except UploadStorageUnavailableError as exc:
        _log_rejection(code="STORAGE_UNAVAILABLE", status_code=503)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage is temporarily unavailable.",
        ) from exc

    logger.info(
        "Claim submission accepted",
        extra={
            "event": "claim.submission.accepted",
            "context": {"status_code": status.HTTP_201_CREATED},
        },
    )
    return ResponseEnvelope(data=ClaimSubmissionResponse.model_validate(claim))


def _log_rejection(*, code: str, status_code: int, **context: object) -> None:
    logger.warning(
        "Claim submission rejected",
        extra={
            "event": "claim.submission.rejected",
            "context": {"code": code, "status_code": status_code, **context},
        },
    )
