"""Database access operations for invoices.

`create_pending` commits through a manually controlled session so the row is
durable before object storage is written. If storage then fails, the invoice
remains visible and queryable instead of being rolled back with the request.
This deliberately favors a detectable missing object over an orphaned object
with no database record.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice, InvoiceStatus


class InvoiceRepository:
    """Repository for performing database operations related to invoices."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self, *, owner_id: UUID, storage_key: str, original_filename: str
    ) -> Invoice:
        """Create a pending invoice row and durably commit it immediately.

        The caller is expected to attempt the storage write only *after*
        this returns, so a storage failure never erases intake evidence.
        """
        invoice = Invoice(
            owner_id=owner_id,
            storage_key=storage_key,
            original_filename=original_filename,
        )
        self._session.add(invoice)
        await self._session.commit()
        await self._session.refresh(invoice)
        return invoice

    async def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Return the invoice associated with an ID, if one exists."""
        return await self._session.get(Invoice, invoice_id)

    async def list_old_pending(
        self, *, cutoff: datetime, limit: int = 100
    ) -> Sequence[Invoice]:
        """Return pending invoices created before a cutoff, oldest first."""
        result = await self._session.execute(
            select(Invoice)
            .where(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.created_at < cutoff,
            )
            .order_by(Invoice.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_upload_failed(self, *, invoice_id: UUID) -> None:
        """Durably record that storage failed for a reserved invoice."""
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(status=InvoiceStatus.UPLOAD_FAILED)
        )
        await self._session.commit()

    async def mark_extraction_failed(self, *, invoice_id: UUID) -> None:
        """Durably record that extraction could not proceed for an invoice."""
        await self._session.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.status == InvoiceStatus.PENDING,
            )
            .values(status=InvoiceStatus.EXTRACTION_FAILED)
        )
        await self._session.commit()

    async def mark_extracted(
        self,
        *,
        invoice_id: UUID,
        fields: dict[str, Any],
        confidence: str,
        confidence_reason: str | None,
    ) -> None:
        """Durably persist extracted fields and mark the invoice as extracted."""
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(
                status=InvoiceStatus.EXTRACTED,
                extracted_fields=fields,
                confidence=confidence,
                confidence_reason=confidence_reason,
            )
        )
        await self._session.commit()
