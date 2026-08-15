"""Evaluate an extracted invoice against every configured deterministic rule."""

from collections.abc import Callable
from datetime import date

from app.services.extraction.model import ExtractedInvoice
from app.services.rules.checks import (
    check_currency_allowed,
    check_invoice_not_future,
    check_invoice_submission_window,
    check_line_item_reconciliation,
    check_max_expense_amount,
)
from app.services.rules.config import RuleConfig
from app.services.rules.result import RuleResult

Check = Callable[[ExtractedInvoice, RuleConfig, date], RuleResult]

_CHECKS: tuple[Check, ...] = (
    check_max_expense_amount,
    check_line_item_reconciliation,
    check_currency_allowed,
    check_invoice_not_future,
    check_invoice_submission_window,
)


class RuleEngine:
    """Evaluate an invoice against the full, fixed set of configured checks."""

    def __init__(
        self, *, config: RuleConfig, checks: tuple[Check, ...] = _CHECKS
    ) -> None:
        self._config = config
        self._checks = checks

    def evaluate(
        self, extracted_invoice: ExtractedInvoice, today: date
    ) -> list[RuleResult]:
        """Return one `RuleResult` per configured rule, in a stable order."""
        return [check(extracted_invoice, self._config, today) for check in self._checks]
