"""Use case for recording a finance reviewer's final decision on an invoice."""

from uuid import UUID

from app.database.models.decision import InvoiceDecision, InvoiceDecisionOutcome
from app.database.repositories.decision import DecisionRepository


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
        return await self._decisions.record(
            invoice_id=invoice_id,
            outcome=outcome,
            reason=reason,
            decided_by_id=decided_by_id,
        )
