"""Routes for policy handbook ingestion and listing."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import (
    PolicyDocumentRepositoryDep,
    PolicyIngestionServiceDep,
    get_current_finance_reviewer,
)
from app.schemas.policy_document import (
    PolicyDocumentListItem,
    PolicyDocumentUploadResponse,
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
) -> PolicyDocumentUploadResponse:
    """Ingest a policy handbook PDF and activate it as the current policy."""
    content = await file.read()
    result = await ingestion.ingest(filename=file.filename or "", content=content)

    logger.info(
        "Policy document activated",
        extra={
            "event": "policy_document.upload.accepted",
            "context": {"chunk_count": result.chunk_count},
        },
    )
    return PolicyDocumentUploadResponse(
        policy_document_id=result.document_id,
        status=result.status,
        chunk_count=result.chunk_count,
    )


@router.get("")
async def list_policy_documents(
    policy_documents: PolicyDocumentRepositoryDep,
) -> list[PolicyDocumentListItem]:
    """List every ingested policy document and its current status."""
    documents = await policy_documents.list_all()
    return [
        PolicyDocumentListItem(
            policy_document_id=document.id,
            status=document.status,
            original_filename=document.original_filename,
            chunk_count=chunk_count,
            created_at=document.created_at,
        )
        for document, chunk_count in documents
    ]
