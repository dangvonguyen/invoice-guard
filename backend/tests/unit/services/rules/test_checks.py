"""Specify each pure deterministic rule check's pass/fail/not_applicable boundaries."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.database.models.rule_result import RuleOutcome
from app.services.rules.checks import (
    check_currency_allowed,
    check_invoice_not_future,
    check_invoice_submission_window,
    check_line_item_reconciliation,
    check_max_expense_amount,
)
from app.services.rules.result import RuleCode
from tests.support.constants import COMPLIANT_INVOICE, RULE_CONFIG, TODAY

pytestmark = pytest.mark.unit


class TestMaxExpenseAmount:
    def should_pass_when_total_amount_equals_the_limit_exactly(self) -> None:
        """Treat an invoice exactly at the spending limit as compliant."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"total_amount": Decimal("1000.00")}
        )

        result = check_max_expense_amount(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS
        assert result.rule_code == RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT

    def should_fail_one_cent_over_the_spending_limit(self) -> None:
        """Flag an invoice exactly one cent over the spending limit."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"total_amount": Decimal("1000.01")}
        )

        result = check_max_expense_amount(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.FAIL
        assert result.rule_code == RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT

    def should_name_the_total_and_the_limit_in_the_failure_message(self) -> None:
        """Surface both figures so the reviewer never has to look them up."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"total_amount": Decimal("1480.00")}
        )

        result = check_max_expense_amount(invoice, RULE_CONFIG, TODAY)

        assert result.message is not None
        assert "1480.00" in result.message
        assert "1000.00" in result.message

    def should_never_return_not_applicable_for_the_spending_limit(self) -> None:
        """Always decide pass/fail - the spending limit is always applicable."""
        under = check_max_expense_amount(
            COMPLIANT_INVOICE.model_copy(update={"total_amount": Decimal("1.00")}),
            RULE_CONFIG,
            TODAY,
        )
        over = check_max_expense_amount(
            COMPLIANT_INVOICE.model_copy(update={"total_amount": Decimal("9999.00")}),
            RULE_CONFIG,
            TODAY,
        )

        assert RuleOutcome.NOT_APPLICABLE not in (under.outcome, over.outcome)


class TestLineItemReconciliation:
    def should_return_not_applicable_when_line_items_is_empty(self) -> None:
        """Record a deliberate non-violation, not a false negative, on receipts."""
        invoice = COMPLIANT_INVOICE.model_copy(update={"line_items": []})

        result = check_line_item_reconciliation(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.NOT_APPLICABLE
        assert result.rule_code == RuleCode.LINE_ITEM_TOTAL_CONSISTENCY

    def should_pass_when_line_items_plus_tax_equal_the_total_exactly(self) -> None:
        """Accept an invoice whose line items and tax reconcile precisely."""
        result = check_line_item_reconciliation(COMPLIANT_INVOICE, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS

    def should_pass_when_the_reconciliation_gap_equals_the_tolerance_exactly(
        self,
    ) -> None:
        """Treat a gap of exactly the configured tolerance as compliant."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"total_amount": Decimal("500.01")}
        )

        result = check_line_item_reconciliation(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS

    def should_fail_when_the_reconciliation_gap_is_one_cent_beyond_tolerance(
        self,
    ) -> None:
        """Flag a gap that exceeds the tolerance by the smallest unit."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"total_amount": Decimal("500.02")}
        )

        result = check_line_item_reconciliation(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.FAIL
        assert result.rule_code == RuleCode.LINE_ITEM_TOTAL_CONSISTENCY

    def should_fail_when_the_total_understates_the_line_items(self) -> None:
        """Flag understatement of the total, not just overstatement."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"total_amount": Decimal("100.00")}
        )

        result = check_line_item_reconciliation(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.FAIL


class TestCurrencyAllowed:
    def should_pass_for_a_currency_in_the_allow_list(self) -> None:
        """Accept a currency that is explicitly allowed."""
        result = check_currency_allowed(COMPLIANT_INVOICE, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS
        assert result.rule_code == RuleCode.CURRENCY_ALLOWED

    def should_pass_for_a_lowercase_form_of_an_allowed_currency(self) -> None:
        """Compare currency codes case-insensitively."""
        invoice = COMPLIANT_INVOICE.model_copy(update={"currency": "usd"})

        result = check_currency_allowed(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS

    def should_fail_naming_the_rejected_code_and_the_allowed_set(self) -> None:
        """Name both the rejected currency and the configured allow-list."""
        invoice = COMPLIANT_INVOICE.model_copy(update={"currency": "JPY"})

        result = check_currency_allowed(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.FAIL
        assert result.message is not None
        assert "JPY" in result.message
        assert "USD" in result.message
        assert "EUR" in result.message
        assert "GBP" in result.message

    def should_never_return_not_applicable_for_currency_allowed(self) -> None:
        """Always decide pass/fail - currency is always applicable."""
        allowed = check_currency_allowed(COMPLIANT_INVOICE, RULE_CONFIG, TODAY)
        rejected = check_currency_allowed(
            COMPLIANT_INVOICE.model_copy(update={"currency": "JPY"}), RULE_CONFIG, TODAY
        )

        assert RuleOutcome.NOT_APPLICABLE not in (allowed.outcome, rejected.outcome)


class TestInvoiceDateNotInFuture:
    def should_pass_for_an_invoice_dated_today(self) -> None:
        """Treat an invoice dated exactly today as not future-dated."""
        invoice = COMPLIANT_INVOICE.model_copy(update={"invoice_date": TODAY})

        result = check_invoice_not_future(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS

    def should_fail_for_an_invoice_dated_tomorrow(self) -> None:
        """Flag an invoice dated one day after today."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"invoice_date": TODAY + timedelta(days=1)}
        )

        result = check_invoice_not_future(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.FAIL
        assert result.rule_code == RuleCode.INVOICE_DATE_NOT_IN_FUTURE

    def should_pass_for_a_date_in_the_past(self) -> None:
        """Leave staleness to the sibling submission-window check."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"invoice_date": TODAY - timedelta(days=1)}
        )

        result = check_invoice_not_future(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS


class TestInvoiceSubmissionWindow:
    def should_pass_for_an_invoice_exactly_max_age_days_old(self) -> None:
        """Treat an invoice exactly at the maximum age as compliant."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"invoice_date": TODAY - timedelta(days=90)}
        )

        result = check_invoice_submission_window(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS

    def should_fail_one_day_past_max_age_days(self) -> None:
        """Flag an invoice one day past the maximum submission age."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"invoice_date": TODAY - timedelta(days=91)}
        )

        result = check_invoice_submission_window(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.FAIL
        assert result.rule_code == RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW

    def should_pass_for_a_future_dated_invoice(self) -> None:
        """Never flag a future-dated invoice as stale - its age is negative."""
        invoice = COMPLIANT_INVOICE.model_copy(
            update={"invoice_date": TODAY + timedelta(days=1)}
        )

        result = check_invoice_submission_window(invoice, RULE_CONFIG, TODAY)

        assert result.outcome == RuleOutcome.PASS
