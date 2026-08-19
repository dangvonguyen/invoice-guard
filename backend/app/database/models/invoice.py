"""Database model for uploaded invoices.

Scope note: intake records distinguish processing uploads from failed storage writes.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.decision import InvoiceDecision
from app.database.models.rule_result import InvoiceRuleResult
from app.database.models.user import User


class InvoiceStatus(StrEnum):
    """Lifecycle states for an invoice."""

    UPLOAD_FAILED = "upload_failed"
    PROCESSING = "processing"
    PROCESSING_ERROR = "processing_error"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExtractionConfidence(StrEnum):
    """Whether an extraction's fields were traceable to the source document."""

    HIGH = "high"
    LOW = "low"


class Invoice(Base):
    """Represent an uploaded invoice document and its intake metadata."""

    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    owner_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        index=True,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=lambda statuses: [s.value for s in statuses],
        ),
        server_default=InvoiceStatus.PROCESSING.value,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    extracted_fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    confidence: Mapped[ExtractionConfidence | None] = mapped_column(
        Enum(
            ExtractionConfidence,
            name="extraction_confidence",
            values_callable=lambda values: [v.value for v in values],
        ),
        nullable=True,
    )
    confidence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped[User] = relationship(lazy="raise")
    # Rely on the FK's ON DELETE CASCADE instead of the ORM nulling out
    # invoice_id first
    rule_results: Mapped[list[InvoiceRuleResult]] = relationship(
        lazy="raise", passive_deletes=True, order_by="InvoiceRuleResult.rule_code"
    )
    decision: Mapped[InvoiceDecision | None] = relationship(
        lazy="raise", passive_deletes=True
    )
