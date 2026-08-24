"""Specify how rule evaluation persists an invoice's rule-result set, independent of extraction."""

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.queueing.jobs.evaluate_rules import evaluate_rules
from app.services.rules.result import RuleCode, RuleOutcome, RuleResult, to_rows
from tests.support.constants import EXTRACTED_INVOICE, TODAY

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

INVOICE_ID = UUID("10000000-0000-0000-0000-000000000001")


async def should_evaluate_the_fields_and_replace_the_invoices_rule_results() -> None:
    """Evaluate against the rule engine and persist the returned result set as-is."""
    rule_results = AsyncMock()
    rule_engine = Mock()
    evaluation = [
        RuleResult(
            rule_code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
            outcome=RuleOutcome.PASS,
        )
    ]
    rule_engine.evaluate.return_value = evaluation

    await evaluate_rules(
        INVOICE_ID,
        extracted_invoice=EXTRACTED_INVOICE,
        rule_results=rule_results,
        rule_engine=rule_engine,
        today=TODAY,
    )

    rule_engine.evaluate.assert_called_once_with(EXTRACTED_INVOICE, TODAY)
    rule_results.replace_for_invoice.assert_awaited_once_with(
        invoice_id=INVOICE_ID, results=to_rows(evaluation)
    )
