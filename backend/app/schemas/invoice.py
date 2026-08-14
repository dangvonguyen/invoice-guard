"""Validation and transfer schemas for invoice API data."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.database.models.invoice import ExtractionConfidence, InvoiceStatus


class InvoiceUploadResponse(BaseModel):
    """Response a successful invoice upload."""

    invoice_id: UUID
    status: InvoiceStatus


class InvoiceDetailResponse(BaseModel):
    """Response for reading once invoice's current state."""

    invoice_id: UUID
    status: InvoiceStatus
    extracted_fields: dict[str, Any] | None
    confidence: ExtractionConfidence | None
    confidence_reason: str | None
