"""Validation and transfer schemas for invoice API data."""

from uuid import UUID

from pydantic import BaseModel

from app.database.models.invoice import InvoiceStatus


class InvoiceUploadResponse(BaseModel):
    """Response a successful invoice upload."""

    invoice_id: UUID
    status: InvoiceStatus
