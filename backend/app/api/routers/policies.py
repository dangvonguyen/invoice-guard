"""Routes for policy handbook ingestion and listing."""

import logging
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import (
    PolicyDocumentRepositoryDep,
    PolicyIngestionServiceDep,
    get_current_finance_reviewer,
)
from app.core.config import get_settings
from app.schemas.envelope import PaginationMeta, ResponseEnvelope
from app.schemas.policy_document import (
    PolicyDocumentListItem,
    PolicyDocumentUploadResponse,
)
from app.services.extraction.text import NoTextLayerError
from app.services.upload.validation import (
    InvalidPayloadError,
    InvalidUploadError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)

router = APIRouter(
    prefix="/policies/documents",
    tags=["Policies"],
    dependencies=[Depends(get_current_finance_reviewer)],
)
logger = logging.getLogger(__name__)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_policy_document(
    ingestion: PolicyIngestionServiceDep, file: Annotated[UploadFile, File()]
) -> ResponseEnvelope[PolicyDocumentUploadResponse]:
    """Ingest a policy handbook PDF and activate it as the current policy."""
    settings = get_settings()
    content = await file.read(settings.POLICY_DOCUMENT_MAX_BYTES + 1)

    try:
        result = await ingestion.ingest(
            filename=file.filename or "",
            content_type=file.content_type,
            content_length=len(content),
            content=content,
        )
    except PayloadTooLargeError as exc:
        _reject_upload(
            exc,
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            reason="payload_too_large",
        )
    except UnsupportedMediaTypeError as exc:
        _reject_upload(
            exc,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            reason="unsupported_media_type",
        )
    except (InvalidPayloadError, InvalidUploadError) as exc:
        _reject_upload(
            exc, status_code=status.HTTP_400_BAD_REQUEST, reason="invalid_upload"
        )
    except NoTextLayerError as exc:
        _reject_upload(
            exc,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            reason="no_text_layer",
        )

    logger.info(
        "Policy document activated",
        extra={
            "event": "policy_document.upload.accepted",
            "context": {"chunk_count": result.chunk_count},
        },
    )
    return ResponseEnvelope(
        data=PolicyDocumentUploadResponse(
            policy_document_id=result.document_id,
            status=result.status,
            chunk_count=result.chunk_count,
        )
    )


def _reject_upload(
    exc: Exception, *, status_code: int, reason: str, detail: str | None = None
) -> NoReturn:
    logger.warning(
        "Policy document upload rejected",
        extra={
            "event": "policy_document.upload.rejected",
            "context": {"reason": reason, "status_code": status_code},
        },
    )
    raise HTTPException(status_code=status_code, detail=detail or str(exc)) from exc


@router.get("")
async def list_policy_documents(
    policy_documents: PolicyDocumentRepositoryDep,
) -> ResponseEnvelope[list[PolicyDocumentListItem], PaginationMeta]:
    """List every ingested policy document and its current status."""
    documents = await policy_documents.list_all()
    items = [
        PolicyDocumentListItem(
            policy_document_id=document.id,
            status=document.status,
            original_filename=document.original_filename,
            chunk_count=chunk_count,
            created_at=document.created_at,
        )
        for document, chunk_count in documents
    ]
    return ResponseEnvelope(data=items)
