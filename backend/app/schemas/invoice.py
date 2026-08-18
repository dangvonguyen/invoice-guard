"""Validation and transfer schemas for invoice API data."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.database.models.invoice import ExtractionConfidence, InvoiceStatus


class InvoiceResponseBase(BaseModel):
    """Common fields shared by every invoice response shape."""

    model_config = {
        "from_attributes": True,
        "validate_by_name": True,
    }

    invoice_id: UUID = Field(validation_alias="id")
    status: InvoiceStatus


class InvoiceUploadResponse(InvoiceResponseBase):
    """Response a successful invoice upload."""


class InvoiceListItem(InvoiceResponseBase):
    """Response for one invoice in an owner's invoice list."""

    created_at: datetime


class InvoiceDetailResponse(InvoiceResponseBase):
    """Response for reading once invoice's current state."""

    extracted_fields: dict[str, Any] | None
    confidence: ExtractionConfidence | None
    confidence_reason: str | None
