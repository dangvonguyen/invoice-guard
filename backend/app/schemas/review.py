"""Reviewer-facing schemas for invoice review."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.database.models.invoice import ExtractionConfidence, InvoiceStatus
from app.schemas.decision import DecisionView


class EmployeeIdentity(BaseModel):
    """Who submitted an invoice, as shown to its reviewer."""

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    email: str


class ReviewFlagView(BaseModel):
    """One reviewer-visible condition produced by analysis."""

    code: str
    summary: str | None
    evidence: dict[str, Any]


class ReviewerInvoiceDetailResponse(BaseModel):
    """Reviewer-facing view of one invoice's current state."""

    id: UUID
    status: InvoiceStatus
    employee: EmployeeIdentity
    extracted_fields: dict[str, Any] | None
    confidence: ExtractionConfidence | None
    confidence_reason: str | None
    review_flags: list[ReviewFlagView]
    decision: DecisionView | None
