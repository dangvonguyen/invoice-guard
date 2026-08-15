"""Evaluate an extracted invoice against configured policy rules and persist the result set."""

from datetime import date
from uuid import UUID

from app.database.repositories.rule_result import RuleResultRepository
from app.services.extraction.model import ExtractedInvoice
from app.services.rules.engine import RuleEngine


async def evaluate_rules(
    invoice_id: UUID,
    *,
    extracted_invoice: ExtractedInvoice,
    rule_results: RuleResultRepository,
    rule_engine: RuleEngine,
    today: date,
) -> None:
    """Evaluate against every configured rule and replace the invoice's stored results."""
    rule_evaluation = rule_engine.evaluate(extracted_invoice, today)

    await rule_results.replace_for_invoice(
        invoice_id=invoice_id, results=rule_evaluation
    )
