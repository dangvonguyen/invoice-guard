"""Routes for invoice document intake."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.deps import (
    CurrentFinanceReviewer,
    CurrentUser,
    DecisionServiceDep,
    ExtractionQueueDep,
    InvoiceIntakeServiceDep,
    InvoiceRepositoryDep,
)
from app.core.config import get_settings
from app.database.models.user import UserRole
from app.queueing import invoice_processing
from app.schemas.decision import DecisionRequest, DecisionView
from app.schemas.envelope import PaginationMeta, ResponseEnvelope
from app.schemas.invoice import (
    InvoiceDetailResponse,
    InvoiceListItem,
    InvoiceUploadResponse,
)
from app.schemas.review import ReviewerInvoiceDetailResponse
from app.services.invoices.views import build_decision_view, resolve_invoice_view
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
        transition = await invoices.mark_processing_error(invoice_id=invoice.id)
        if transition.status is not None:
            invoice.status = transition.status

    logger.info(
        "Invoice upload accepted",
        extra={
            "event": "invoice.upload.accepted",
            "context": {"status_code": status.HTTP_201_CREATED},
        },
    )
    return ResponseEnvelope(data=InvoiceUploadResponse.model_validate(invoice))


@router.get("")
async def list_invoices(
    current_user: CurrentUser,
    repository: InvoiceRepositoryDep,
    offset: int = 0,
    limit: int = 10,
) -> ResponseEnvelope[list[InvoiceListItem], PaginationMeta]:
    """List invoices owned by the authenticated user, newest first."""
    invoices, total = await repository.list_for_owner(current_user.id, offset, limit)
    return ResponseEnvelope(
        data=[InvoiceListItem.model_validate(inv) for inv in invoices],
        meta=PaginationMeta(total=total, offset=offset, limit=limit),
    )


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    current_user: CurrentUser,
    invoices: InvoiceRepositoryDep,
) -> ResponseEnvelope[InvoiceDetailResponse | ReviewerInvoiceDetailResponse, None]:
    """Return an invoice the caller owns, or - for a reviewer - any invoice."""
    is_reviewer = current_user.role == UserRole.FINANCE_REVIEWER
    invoice = (
        await invoices.get_for_review_view(invoice_id)
        if is_reviewer
        else await invoices.get_for_employee_view(invoice_id)
    )
    view = resolve_invoice_view(
        invoice, current_user_id=current_user.id, is_reviewer=is_reviewer
    )
    return ResponseEnvelope(data=view)


@router.post("/{invoice_id}/decision", status_code=status.HTTP_201_CREATED)
async def decide_invoice(
    invoice_id: UUID,
    payload: DecisionRequest,
    reviewer: CurrentFinanceReviewer,
    decision_service: DecisionServiceDep,
) -> ResponseEnvelope[DecisionView, None]:
    """Record a finance reviewer's one final decision on an invoice."""
    decision = await decision_service.decide(
        invoice_id=invoice_id,
        outcome=payload.outcome,
        reason=payload.reason,
        decided_by_id=reviewer.id,
    )
    return ResponseEnvelope(data=build_decision_view(decision))


def _log_rejection(*, code: str, status_code: int, **context: object) -> None:
    logger.warning(
        "Invoice upload rejected",
        extra={
            "event": "invoice.upload.rejected",
            "context": {"code": code, "status_code": status_code, **context},
        },
    )
