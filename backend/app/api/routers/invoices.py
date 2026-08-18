"""Routes for invoice document intake."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.deps import (
    CurrentUser,
    ExtractionQueueDep,
    InvoiceIntakeServiceDep,
    InvoiceRepositoryDep,
)
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.database.models.invoice import InvoiceStatus
from app.queueing import invoice_processing
from app.schemas.envelope import PaginationMeta, ResponseEnvelope
from app.schemas.invoice import (
    InvoiceDetailResponse,
    InvoiceListItem,
    InvoiceUploadResponse,
)
from app.services.upload.intake import (
    UploadRateLimitExceededError,
    UploadStorageUnavailableError,
)
from app.services.upload.validation import InvalidUploadError

router = APIRouter(prefix="/invoices", tags=["Invoices"])
logger = logging.getLogger(__name__)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    current_user: CurrentUser,
    invoice_intake: InvoiceIntakeServiceDep,
    extraction_queue: ExtractionQueueDep,
    invoices: InvoiceRepositoryDep,
    file: Annotated[UploadFile, File()],
) -> ResponseEnvelope[InvoiceUploadResponse, None]:
    """Accept an invoice document and enqueue it for processing."""
    settings = get_settings()
    content = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    try:
        invoice = await invoice_intake.accept(
            owner_id=current_user.id,
            filename=file.filename,
            content_type=file.content_type,
            content_length=len(content),
            content=content,
        )
    except UploadRateLimitExceededError as exc:
        _log_rejection(
            code=exc.code,
            status_code=exc.status_code,
            limit=settings.UPLOAD_RATE_LIMIT,
            window_seconds=settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
        )
        raise
    except InvalidUploadError as exc:
        _log_rejection(code=exc.code, status_code=exc.status_code)
        raise
    except UploadStorageUnavailableError as exc:
        _log_rejection(
            code="STORAGE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invoice storage is temporarily unavailable. Try again shortly.",
        ) from exc

    try:
        await run_in_threadpool(
            invoice_processing.enqueue, extraction_queue, invoice.id
        )
    except invoice_processing.ProcessingEnqueueError:
        logger.warning(
            "Invoice extraction enqueue failed",
            extra={
                "event": "invoice.extraction.enqueue_failed",
                "context": {"invoice_id": str(invoice.id)},
            },
        )
        await invoices.mark_processing_error(invoice_id=invoice.id)
        invoice.status = InvoiceStatus.PROCESSING_ERROR

    logger.info(
        "Invoice upload accepted",
        extra={
            "event": "invoice.upload.accepted",
            "context": {"status_code": status.HTTP_201_CREATED},
        },
    )
    return ResponseEnvelope(
        data=InvoiceUploadResponse(invoice_id=invoice.id, status=invoice.status)
    )


@router.get("")
async def list_invoices(
    current_user: CurrentUser,
    repository: InvoiceRepositoryDep,
    offset: int = 0,
    limit: int = 10,
) -> ResponseEnvelope[list[InvoiceListItem], PaginationMeta]:
    """List invoices owned by the authenticated user, newest first."""
    invoices = await repository.list_for_owner(current_user.id, offset, limit)
    return ResponseEnvelope(
        data=[InvoiceListItem.model_validate(inv) for inv in invoices],
        meta=PaginationMeta(total=len(invoices), offset=offset, limit=limit),
    )


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    current_user: CurrentUser,
    invoices: InvoiceRepositoryDep,
) -> ResponseEnvelope[InvoiceDetailResponse, None]:
    """Return an invoice owned by the authenticated user."""
    invoice = await invoices.get_by_id(invoice_id)
    if invoice is None or invoice.owner_id != current_user.id:
        raise NotFoundError("Invoice not found")

    return ResponseEnvelope(
        data=InvoiceDetailResponse(
            invoice_id=invoice.id,
            status=invoice.status,
            extracted_fields=invoice.extracted_fields,
            confidence=invoice.confidence,
            confidence_reason=invoice.confidence_reason,
        )
    )


def _log_rejection(*, code: str, status_code: int, **context: object) -> None:
    logger.warning(
        "Invoice upload rejected",
        extra={
            "event": "invoice.upload.rejected",
            "context": {"code": code, "status_code": status_code, **context},
        },
    )
