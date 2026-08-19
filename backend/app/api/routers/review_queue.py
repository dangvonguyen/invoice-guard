"""Routes for the finance reviewer's queue of invoices awaiting review."""

from fastapi import APIRouter, Depends

from app.api.deps import InvoiceRepositoryDep, get_current_finance_reviewer
from app.schemas.envelope import PaginationMeta, ResponseEnvelope
from app.schemas.invoice import ReviewQueueItem
from app.services.invoices.views import build_invoice_summary

router = APIRouter(
    prefix="/review-queue",
    tags=["Review Queue"],
    dependencies=[Depends(get_current_finance_reviewer)],
)


@router.get("")
async def list_review_queue(
    invoices: InvoiceRepositoryDep,
    offset: int = 0,
    limit: int = 100,
) -> ResponseEnvelope[list[ReviewQueueItem], PaginationMeta]:
    """List invoices awaiting review, oldest first."""
    rows, total = await invoices.list_awaiting_review(offset, limit)
    items = [
        ReviewQueueItem(
            id=invoice.id,
            status=invoice.status,
            submitted_at=invoice.created_at,
            invoice_summary=build_invoice_summary(invoice),
            flag_count=flag_count,
        )
        for invoice, flag_count in rows
    ]
    return ResponseEnvelope(
        data=items,
        meta=PaginationMeta(total=total, offset=offset, limit=limit),
    )
