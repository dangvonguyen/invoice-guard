"""Database access operations for invoice decisions."""

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.decision import InvoiceDecision, InvoiceDecisionOutcome
from app.database.models.invoice import Invoice, InvoiceStatus

_OUTCOME_TO_STATUS = {
    InvoiceDecisionOutcome.APPROVED: InvoiceStatus.APPROVED,
    InvoiceDecisionOutcome.REJECTED: InvoiceStatus.REJECTED,
}


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

        await self._session.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.status == InvoiceStatus.AWAITING_REVIEW,
            )
            .values(status=_OUTCOME_TO_STATUS[outcome])
        )

        await self._session.commit()
        await self._session.refresh(decision)
        return decision
