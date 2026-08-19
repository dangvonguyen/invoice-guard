"""Use case for recording a finance reviewer's final decision on an invoice."""

from uuid import UUID

from app.core.errors import DomainError
from app.database.models.decision import InvoiceDecision, InvoiceDecisionOutcome
from app.database.repositories.decision import (
    DecisionAlreadyExistsError,
    DecisionRepository,
)


class AlreadyDecidedError(DomainError):
    """Raised when the invoice already carries a final decision."""

    code = "INVOICE_ALREADY_DECIDED"
    status_code = 409


class DecisionService:
    """Durable recording of a review decision."""

    def __init__(self, decisions: DecisionRepository) -> None:
        self._decisions = decisions

    async def decide(
        self,
        *,
        invoice_id: UUID,
        outcome: InvoiceDecisionOutcome,
        reason: str,
        decided_by_id: UUID,
    ) -> InvoiceDecision:
        """Record the one final decision for an invoice, or raise why not."""
        try:
            return await self._decisions.record(
                invoice_id=invoice_id,
                outcome=outcome,
                reason=reason,
                decided_by_id=decided_by_id,
            )
        except DecisionAlreadyExistsError as exc:
            existing = await self._decisions.get_by_invoice(invoice_id)
            message = f"Invoice {invoice_id} already has a final decision."
            if existing is not None:
                message = (
                    f"Invoice {invoice_id} was already {existing.outcome} "
                    f"by {existing.decided_by.name}."
                )
            raise AlreadyDecidedError(message) from exc
