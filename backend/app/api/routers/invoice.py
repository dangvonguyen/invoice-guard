"""Routes for invoice document intake."""

import logging
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from redis.exceptions import RedisError

from app.api.deps import (
    CurrentUser,
    ExtractionQueueDep,
    InvoiceIntakeServiceDep,
    InvoiceRepositoryDep,
)
from app.core.config import get_settings
from app.database.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceDetailResponse, InvoiceUploadResponse
from app.services.invoice_intake import (
    InvoiceStorageUnavailableError,
    UploadRateLimitExceededError,
)
from app.services.invoice_mime_validator import (
    InvoiceValidationError,
    PayloadTooLargeError,
    UnreadableUploadError,
    UnsupportedMediaTypeError,
)
from app.workers.jobs import run_extraction_job

router = APIRouter(prefix="/invoices", tags=["Invoices"])
logger = logging.getLogger(__name__)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    current_user: CurrentUser,
    invoice_intake: InvoiceIntakeServiceDep,
    extraction_queue: ExtractionQueueDep,
    invoices: InvoiceRepositoryDep,
    file: Annotated[UploadFile, File()],
) -> InvoiceUploadResponse:
    """Accept an invoice document and enqueue it for processing."""
    settings = get_settings()
    content = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    try:
        invoice = await invoice_intake.upload(
            owner_id=current_user.id,
            filename=file.filename,
            content_type=file.content_type,
            size=len(content),
            content=content,
        )
    except UploadRateLimitExceededError as exc:
        _reject_upload(
            exc,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            reason="rate_limited",
            detail="Upload rate limit exceeded. Try again shortly.",
            limit=settings.UPLOAD_RATE_LIMIT,
            window_seconds=settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
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
    except (UnreadableUploadError, InvoiceValidationError) as exc:
        _reject_upload(
            exc,
            status_code=status.HTTP_400_BAD_REQUEST,
            reason="invalid_upload",
        )
    except InvoiceStorageUnavailableError as exc:
        _reject_upload(
            exc,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            reason="storage_unavailable",
            detail="Invoice storage is temporarily unavailable. Try again shortly.",
        )

    try:
        await run_in_threadpool(
            extraction_queue.enqueue, run_extraction_job, str(invoice.id)
        )
    except RedisError:
        logger.warning(
            "Invoice extraction enqueue failed",
            extra={
                "event": "invoice.extraction.enqueue_failed",
                "context": {"invoice_id": str(invoice.id)},
            },
        )
        await invoices.mark_extraction_failed(invoice_id=invoice.id)
        invoice.status = InvoiceStatus.EXTRACTION_FAILED

    logger.info(
        "Invoice upload accepted",
        extra={
            "event": "invoice.upload.accepted",
            "context": {"status_code": status.HTTP_201_CREATED},
        },
    )
    return InvoiceUploadResponse(invoice_id=invoice.id, status=invoice.status)


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    current_user: CurrentUser,
    invoices: InvoiceRepositoryDep,
) -> InvoiceDetailResponse:
    """Return an invoice owned by the authenticated user."""
    invoice = await invoices.get_by_id(invoice_id)
    if invoice is None or invoice.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    return InvoiceDetailResponse(
        invoice_id=invoice.id,
        status=invoice.status,
        extracted_fields=invoice.extracted_fields,
        confidence=invoice.confidence,
        confidence_reason=invoice.confidence_reason,
    )


def _reject_upload(
    exc: Exception,
    *,
    status_code: int,
    reason: str,
    detail: str | None = None,
    **context: object,
) -> NoReturn:
    logger.warning(
        "Invoice upload rejected",
        extra={
            "event": "invoice.upload.rejected",
            "context": {"reason": reason, "status_code": status_code, **context},
        },
    )

    raise HTTPException(status_code=status_code, detail=detail or str(exc)) from exc
