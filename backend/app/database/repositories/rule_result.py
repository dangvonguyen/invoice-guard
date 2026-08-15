"""Database access operations for invoice rule-evaluation results."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.rule_result import InvoiceRuleResult
from app.services.rules.result import RuleResult


class RuleResultRepository:
    """Repository for performing database operations related to rule results."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_invoice(
        self, *, invoice_id: UUID, results: Sequence[RuleResult]
    ) -> None:
        """Replace all of an invoice's rule-result rows with a fresh set."""
        await self._session.execute(
            delete(InvoiceRuleResult).where(InvoiceRuleResult.invoice_id == invoice_id)
        )
        self._session.add_all(
            [
                InvoiceRuleResult(
                    invoice_id=invoice_id,
                    rule_code=result.rule_code.value,
                    outcome=result.outcome,
                    message=result.message,
                )
                for result in results
            ]
        )
        await self._session.commit()

    async def list_by_invoice(self, invoice_id: UUID) -> Sequence[InvoiceRuleResult]:
        """Return every rule-result row for an invoice, in a stable order."""
        result = await self._session.execute(
            select(InvoiceRuleResult)
            .where(InvoiceRuleResult.invoice_id == invoice_id)
            .order_by(InvoiceRuleResult.rule_code)
        )
        return result.scalars().all()
