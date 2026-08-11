"""Database access operations for invoices.

`create_pending` commits through a manually controlled session so the row is
durable before object storage is written. If storage then fails, the invoice
remains visible and queryable instead of being rolled back with the request.
This deliberately favors a detectable missing object over an orphaned object
with no database record.
"""

from uuid import UUID

from sqlalchemy import update
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

    async def mark_upload_failed(self, *, invoice_id: UUID) -> None:
        """Durably record that storage failed for a reserved invoice."""
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(status=InvoiceStatus.UPLOAD_FAILED)
        )
        await self._session.commit()
