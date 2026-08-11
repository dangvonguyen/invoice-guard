"""Database model for uploaded invoices.

Scope note: intake records distinguish pending uploads from failed storage writes.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InvoiceStatus(StrEnum):
    """Lifecycle states for an invoice."""

    PENDING = "pending"
    UPLOAD_FAILED = "upload_failed"
    EXTRACTED = "extracted"


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
        server_default=InvoiceStatus.PENDING.value,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    extraction_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
