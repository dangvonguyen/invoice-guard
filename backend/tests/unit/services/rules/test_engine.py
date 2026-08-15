"""Specify how the rule engine orchestrates the full, fixed set of checks."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.extraction.model import ExtractedInvoice, ExtractedLineItem
from app.services.rules.config import RuleConfig
from app.services.rules.engine import RuleEngine
from app.services.rules.result import RuleCode

pytestmark = pytest.mark.unit

TODAY = date(2026, 8, 15)

CONFIG = RuleConfig(
    max_expense_amount=Decimal("1000.00"),
    max_expense_age_days=90,
    allowed_currencies=frozenset({"USD", "EUR", "GBP"}),
    reconciliation_tolerance=Decimal("0.01"),
)

COMPLIANT_INVOICE = ExtractedInvoice(
    vendor_name="Acme Supplies",
    invoice_date=date(2026, 7, 30),
    total_amount=Decimal("486.00"),
    currency="USD",
    tax_amount=Decimal("36.00"),
    line_items=[
        ExtractedLineItem(description="Standing desk riser", amount=Decimal("320.00")),
        ExtractedLineItem(description="Monitor arm", amount=Decimal("130.00")),
    ],
)


def should_return_exactly_one_result_per_configured_rule_code() -> None:
    """Never return a variable-length list of only the broken rules."""
    engine = RuleEngine(config=CONFIG)

    results = engine.evaluate(COMPLIANT_INVOICE, TODAY)

    assert {result.rule_code for result in results} == set(RuleCode)
    assert len(results) == len(RuleCode)


def should_be_pure_returning_the_same_result_for_the_same_input() -> None:
    """Produce identical results for identical fields and evaluation date."""
    engine = RuleEngine(config=CONFIG)

    first = engine.evaluate(COMPLIANT_INVOICE, TODAY)
    second = engine.evaluate(COMPLIANT_INVOICE, TODAY)

    assert first == second
