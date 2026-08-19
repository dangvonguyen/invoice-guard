"""Database access operations for invoice rule-evaluation results."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.rule_result import InvoiceRuleResult
from app.services.rules.result import EvidenceValue, RuleResult


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
                    evidence=self._to_json(result.evidence),
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

    @staticmethod
    def _to_json(evidence: dict[str, EvidenceValue]) -> dict[str, Any]:
        """Convert types into JSON-safe values for storage."""
        serialized: dict[str, Any] = {}
        for key, value in evidence.items():
            if isinstance(value, str | int):
                serialized[key] = value
            elif isinstance(value, Decimal | date | UUID):
                serialized[key] = str(value)
            else:
                serialized[key] = list(value)
        return serialized
