"""Routes for claim submission and an owner's read-only view of their claims."""

import logging
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.deps import (
    ClaimRepositoryDep,
    ClaimSubmissionServiceDep,
    CurrentUser,
    StorageClientDep,
)
from app.api.openapi import UNAUTHORIZED_RESPONSE
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.storage import StorageWriteError
from app.schemas.claim import (
    ClaimCreateRequest,
    ClaimCreateResponse,
    ClaimResponse,
    ClaimSummary,
)
from app.schemas.envelope import PaginationMeta, ResponseEnvelope
from app.services.claims.submission import ClaimSubmissionRateLimitExceededError
from app.services.claims.views import to_claim_response
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


@router.get("")
async def list_claims(
    current_user: CurrentUser,
    claim_repo: ClaimRepositoryDep,
    needs_action: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ResponseEnvelope[list[ClaimSummary], PaginationMeta]:
    """List the caller's claims, newest first."""
    claims, total = await claim_repo.list_for_owner(
        current_user.id, offset, limit, needs_action=needs_action
    )

    return ResponseEnvelope(
        data=[ClaimSummary.model_validate(claim) for claim in claims],
        meta=PaginationMeta(total=total, offset=offset, limit=limit),
    )


@router.get("/{claim_id}")
async def get_claim(
    claim_id: UUID,
    current_user: CurrentUser,
    claim_repo: ClaimRepositoryDep,
) -> ResponseEnvelope[ClaimResponse, None]:
    """Return one claim owned by the caller."""
    claim = await claim_repo.get_for_owner(claim_id, current_user.id)

    if claim is None:
        raise NotFoundError(f"claim {claim_id} not found")

    return ResponseEnvelope(data=to_claim_response(claim))


@router.get("/{claim_id}/attachment")
async def get_claim_attachment(
    claim_id: UUID,
    current_user: CurrentUser,
    claim_repo: ClaimRepositoryDep,
    storage: StorageClientDep,
) -> Response:
    """Return the attachment for a claim owned by the caller."""
    claim = await claim_repo.get_for_owner(claim_id, current_user.id)

    if claim is None:
        raise NotFoundError(f"claim {claim_id} not found")

    try:
        content = await storage.read(key=claim.attachment_key)
    except StorageWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage is temporarily unavailable.",
        ) from exc

    filename = quote(claim.attachment_filename, safe="")
    return Response(
        content=content,
        media_type=claim.attachment_content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
        },
    )


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
