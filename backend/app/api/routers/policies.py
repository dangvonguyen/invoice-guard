"""Routes for policy handbook ingestion and listing."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import (
    PolicyDocumentRepositoryDep,
    PolicyIngestionServiceDep,
    get_current_finance_reviewer,
)
from app.core.config import get_settings
from app.schemas.envelope import ResponseEnvelope
from app.schemas.policy_document import (
    PolicyDocumentListItem,
    PolicyDocumentUploadResponse,
)
from app.services.extraction.text import NoTextLayerError
from app.services.upload.validation import InvalidUploadError

router = APIRouter(
    prefix="/policies/documents",
    tags=["Policies"],
    dependencies=[Depends(get_current_finance_reviewer)],
)
logger = logging.getLogger(__name__)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_policy_document(
    ingestion: PolicyIngestionServiceDep, file: Annotated[UploadFile, File()]
) -> ResponseEnvelope[PolicyDocumentUploadResponse, None]:
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
    except (InvalidUploadError, NoTextLayerError) as exc:
        logger.warning(
            "Policy document upload rejected",
            extra={
                "event": "policy_document.upload.rejected",
                "context": {"code": exc.code, "status_code": exc.status_code},
            },
        )
        raise

    logger.info(
        "Policy document activated",
        extra={
            "event": "policy_document.upload.accepted",
            "context": {"chunk_count": result.chunk_count},
        },
    )
    return ResponseEnvelope(
        data=PolicyDocumentUploadResponse(
            id=result.document_id,
            status=result.status,
            chunk_count=result.chunk_count,
        )
    )


@router.get("")
async def list_policy_documents(
    policy_documents: PolicyDocumentRepositoryDep,
) -> ResponseEnvelope[list[PolicyDocumentListItem], None]:
    """List every ingested policy document and its current status."""
    documents = await policy_documents.list_all()
    items = [
        PolicyDocumentListItem(
            id=document.id,
            status=document.status,
            original_filename=document.original_filename,
            chunk_count=chunk_count,
            created_at=document.created_at,
        )
        for document, chunk_count in documents
    ]
    return ResponseEnvelope(data=items)
