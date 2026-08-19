"""Database access operations for invoice decisions."""

from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.decision import InvoiceDecision, InvoiceDecisionOutcome
from app.database.models.invoice import Invoice, InvoiceStatus

_OUTCOME_TO_STATUS = {
    InvoiceDecisionOutcome.APPROVED: InvoiceStatus.APPROVED,
    InvoiceDecisionOutcome.REJECTED: InvoiceStatus.REJECTED,
}


class DecisionAlreadyExistsError(Exception):
    """Raised when an invoice already has a decision recorded against it."""


class InvoiceNotAwaitingReviewError(Exception):
    """Raised when the target invoice was not in `awaiting_review`."""


class DecisionRepository:
    """Repository for performing database operations related to decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        invoice_id: UUID,
        outcome: InvoiceDecisionOutcome,
        reason: str,
        decided_by_id: UUID,
    ) -> InvoiceDecision:
        """Insert a decision and transition the invoice status, atomically."""
        decision = InvoiceDecision(
            invoice_id=invoice_id,
            outcome=outcome,
            reason=reason,
            decided_by_id=decided_by_id,
        )
        self._session.add(decision)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DecisionAlreadyExistsError(str(invoice_id)) from exc

        result = await self._session.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.status == InvoiceStatus.AWAITING_REVIEW,
            )
            .values(status=_OUTCOME_TO_STATUS[outcome])
        )
        if cast(CursorResult[None], result).rowcount == 0:
            await self._session.rollback()
            raise InvoiceNotAwaitingReviewError(str(invoice_id))

        await self._session.commit()
        await self._session.refresh(decision, attribute_names=["decided_by"])
        return decision

    async def get_by_invoice(self, invoice_id: UUID) -> InvoiceDecision | None:
        """Return an invoice's decision, with the deciding reviewer loaded."""
        result = await self._session.execute(
            select(InvoiceDecision)
            .where(InvoiceDecision.invoice_id == invoice_id)
            .options(selectinload(InvoiceDecision.decided_by))
        )
        return result.scalar_one_or_none()
