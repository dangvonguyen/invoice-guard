"""Database access operations for invoice rule-evaluation results."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome


@dataclass(frozen=True)
class RuleResultRow:
    """One rule's outcome, already JSON-safe and ready to persist."""

    rule_code: str
    outcome: RuleOutcome
    evidence: dict[str, Any] = field(default_factory=dict)


class RuleResultRepository:
    """Repository for performing database operations related to rule results."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_invoice(
        self, *, invoice_id: UUID, results: Sequence[RuleResultRow]
    ) -> None:
        """Replace all of an invoice's rule-result rows with a fresh set."""
        await self._session.execute(
            delete(InvoiceRuleResult).where(InvoiceRuleResult.invoice_id == invoice_id)
        )
        self._session.add_all(
            [
                InvoiceRuleResult(
                    invoice_id=invoice_id,
                    rule_code=result.rule_code,
                    outcome=result.outcome,
                    evidence=result.evidence,
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
