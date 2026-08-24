"""The single table of rule definitions the engine and reviewer-facing flag
summaries both read from.

Adding or changing a rule means adding or editing exactly one `RuleDefinition`
entry in `RULES` (plus the check function itself, which is the rule's actual
logic, not wiring).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType

from app.database.models.rule_result import RuleOutcome
from app.services.extraction.model import ExtractedInvoice
from app.services.rules.checks import (
    check_currency_allowed,
    check_invoice_not_future,
    check_invoice_submission_window,
    check_line_item_reconciliation,
    check_max_expense_amount,
)
from app.services.rules.config import RuleConfig
from app.services.rules.result import RuleCode, RuleResult

Check = Callable[[ExtractedInvoice, RuleConfig, date], RuleResult]


@dataclass(frozen=True)
class RuleDefinition:
    """One rule's identity, check logic, and reviewer-facing outcome summaries."""

    code: RuleCode
    check: Check
    summaries: Mapping[RuleOutcome, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    explainable: bool = False


RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
        check=check_max_expense_amount,
        summaries=MappingProxyType(
            {
                RuleOutcome.FAIL: "Invoice total exceeds the configured review limit.",
            }
        ),
        explainable=True,
    ),
    RuleDefinition(
        code=RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
        check=check_line_item_reconciliation,
        summaries=MappingProxyType(
            {
                RuleOutcome.FAIL: (
                    "Line items and tax do not reconcile with the stated total."
                ),
                RuleOutcome.NOT_APPLICABLE: (
                    "No line items were extracted to reconcile against the total."
                ),
            }
        ),
    ),
    RuleDefinition(
        code=RuleCode.CURRENCY_ALLOWED,
        check=check_currency_allowed,
        summaries=MappingProxyType(
            {
                RuleOutcome.FAIL: "Invoice currency is not in the allowed set.",
            }
        ),
        explainable=True,
    ),
    RuleDefinition(
        code=RuleCode.INVOICE_DATE_NOT_IN_FUTURE,
        check=check_invoice_not_future,
        summaries=MappingProxyType(
            {
                RuleOutcome.FAIL: "Invoice is dated in the future.",
            }
        ),
    ),
    RuleDefinition(
        code=RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW,
        check=check_invoice_submission_window,
        summaries=MappingProxyType(
            {
                RuleOutcome.FAIL: (
                    "Invoice was submitted after the allowed submission window."
                ),
            }
        ),
        explainable=True,
    ),
)
