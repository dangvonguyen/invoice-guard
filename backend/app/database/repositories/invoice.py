"""Database access operations for invoices.

`create_processing` commits through a manually controlled session so the row is
durable before object storage is written. If storage then fails, the invoice
remains visible and queryable instead of being rolled back with the request.
This deliberately favors a detectable missing object over an orphaned object
with no database record.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.decision import InvoiceDecision
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome


class InvoiceRepository:
    """Repository for performing database operations related to invoices."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_processing(
        self, *, owner_id: UUID, storage_key: str, original_filename: str
    ) -> Invoice:
        """Create a processing invoice row and durably commit it immediately.

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

    async def get_for_review_view(self, invoice_id: UUID) -> Invoice | None:
        """Return an invoice with its owner, rule results, and decision loaded."""
        result = await self._session.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                selectinload(Invoice.owner),
                selectinload(Invoice.rule_results),
                selectinload(Invoice.decision).selectinload(InvoiceDecision.decided_by),
            )
        )
        return result.scalar_one_or_none()

    async def get_for_employee_view(self, invoice_id: UUID) -> Invoice | None:
        """Return an invoice with only its decision loaded, for the owner's view."""
        result = await self._session.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                selectinload(Invoice.decision).selectinload(InvoiceDecision.decided_by)
            )
        )
        return result.scalar_one_or_none()

    async def list_for_owner(
        self, owner_id: UUID, offset: int, limit: int
    ) -> tuple[Sequence[Invoice], int]:
        """Return a page of an owner's invoices and the total count.

        Newest first. Excludes failed uploads
        """
        owner_filter = (
            Invoice.owner_id == owner_id,
            Invoice.status != InvoiceStatus.UPLOAD_FAILED,
        )
        result = await self._session.execute(
            select(Invoice, func.count().over().label("total"))
            .where(*owner_filter)
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.all()
        if rows:
            return [invoice for invoice, _ in rows], rows[0].total

        total = await self._session.scalar(
            select(func.count()).select_from(Invoice).where(*owner_filter)
        )
        return [], total or 0

    async def list_awaiting_review(
        self, offset: int, limit: int
    ) -> tuple[Sequence[tuple[Invoice, int]], int]:
        """Return a page of awaiting-review invoices with flag counts, and the total.

        Oldest first. The total reflects the full matching set, not just the
        page, computed via a window function alongside the page query.
        """
        flag_counts = (
            select(
                InvoiceRuleResult.invoice_id,
                func.count().label("flag_count"),
            )
            .where(InvoiceRuleResult.outcome == RuleOutcome.FAIL)
            .group_by(InvoiceRuleResult.invoice_id)
            .subquery()
        )
        awaiting_review = Invoice.status == InvoiceStatus.AWAITING_REVIEW
        result = await self._session.execute(
            select(
                Invoice,
                func.coalesce(flag_counts.c.flag_count, 0),
                func.count().over().label("total"),
            )
            .outerjoin(flag_counts, flag_counts.c.invoice_id == Invoice.id)
            .where(awaiting_review)
            .order_by(Invoice.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.all()
        if rows:
            return [(invoice, count) for invoice, count, _ in rows], rows[0].total

        total = await self._session.scalar(
            select(func.count()).select_from(Invoice).where(awaiting_review)
        )
        return [], total or 0

    async def list_old_processing(
        self, *, cutoff: datetime, limit: int = 100
    ) -> Sequence[Invoice]:
        """Return processing invoices created before a cutoff, oldest first."""
        result = await self._session.execute(
            select(Invoice)
            .where(
                Invoice.status == InvoiceStatus.PROCESSING,
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

    async def mark_processing_error(self, *, invoice_id: UUID) -> None:
        """Durably record that extraction could not proceed for an invoice."""
        await self._session.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.status == InvoiceStatus.PROCESSING,
                # Guarded so a later retry/failure callback can never stomp
                # on fields a prior attempt already persisted
                Invoice.extracted_fields.is_(None),
            )
            .values(status=InvoiceStatus.PROCESSING_ERROR)
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
        """Durably persist extracted fields without changing invoice status.

        The status transition off `processing` happens once rule
        evaluation also completes, not here.
        """
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(
                extracted_fields=fields,
                confidence=confidence,
                confidence_reason=confidence_reason,
            )
        )
        await self._session.commit()

    async def mark_awaiting_review(self, *, invoice_id: UUID) -> None:
        """Durably open an invoice for review, whether analysis completed or not.

        Used both for a fully analyzed invoice and for retry-exhausted ones
        that never finished analysis - either way, a reviewer decides next.
        """
        await self._session.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.status.in_(
                    [InvoiceStatus.PROCESSING, InvoiceStatus.PROCESSING_ERROR]
                ),
            )
            .values(status=InvoiceStatus.AWAITING_REVIEW)
        )
        await self._session.commit()
