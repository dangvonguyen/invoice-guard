"""Validation and transfer schemas for invoice API data."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.database.models.invoice import InvoiceStatus


class InvoiceResponseBase(BaseModel):
    """Common fields shared by every invoice response shape."""

    model_config = {
        "from_attributes": True,
    }

    id: UUID
    status: InvoiceStatus


class InvoiceUploadResponse(InvoiceResponseBase):
    """Response a successful invoice upload."""


class InvoiceListItem(InvoiceResponseBase):
    """Response for one invoice in an owner's invoice list."""

    created_at: datetime


class InvoiceSummary(BaseModel):
    """The plain-language invoice facts an employee is allowed to see."""

    vendor_name: str
    invoice_date: date
    total_amount: Decimal
    currency: str


class InvoiceDetailResponse(InvoiceResponseBase):
    """Employee-facing view of one invoice's current state."""

    invoice_summary: InvoiceSummary | None
    decision: None = None


class ReviewQueueItem(InvoiceResponseBase):
    """Response for one invoice in the finance reviewer's review queue."""

    submitted_at: datetime
    invoice_summary: InvoiceSummary | None
    flag_count: int
