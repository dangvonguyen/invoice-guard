"""Pure, deterministic checks against already-extracted invoice fields.

Every check takes an `ExtractedInvoice`, a `RuleConfig`, and the evaluation
date, and returns a `RuleResult`.
"""

from datetime import date
from decimal import Decimal

from app.database.models.rule_result import RuleOutcome
from app.services.extraction.model import ExtractedInvoice
from app.services.rules.config import RuleConfig
from app.services.rules.result import RuleCode, RuleResult


def check_max_expense_amount(
    extracted_voice: ExtractedInvoice, config: RuleConfig, today: date
) -> RuleResult:
    """Flag an invoice total that exceeds the configured spending limit."""
    del today
    if extracted_voice.total_amount <= config.max_expense_amount:
        return RuleResult(
            rule_code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT, outcome=RuleOutcome.PASS
        )
    return RuleResult(
        rule_code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
        outcome=RuleOutcome.FAIL,
        message=(
            f"Invoice total {extracted_voice.total_amount} exceeds the configured "
            f"spending limit of {config.max_expense_amount}"
        ),
    )


def check_line_item_reconciliation(
    extracted_voice: ExtractedInvoice, config: RuleConfig, today: date
) -> RuleResult:
    """Flag line items and tax that fail to reconcile with the stated total.

    An empty `line_items` list means there is no evidence to reconcile
    against, not that the invoice is wrong, so it is `not_applicable` rather
    than a false-positive `fail`.
    """
    del today

    if not extracted_voice.line_items:
        return RuleResult(
            rule_code=RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
            outcome=RuleOutcome.NOT_APPLICABLE,
            message="No line items were extracted to reconcile against the total",
        )

    reconciled = (
        sum((item.amount for item in extracted_voice.line_items), Decimal(0))
        + extracted_voice.tax_amount
    )
    gap = abs(reconciled - extracted_voice.total_amount)
    if gap <= config.reconciliation_tolerance:
        return RuleResult(
            rule_code=RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
            outcome=RuleOutcome.PASS,
        )
    return RuleResult(
        rule_code=RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
        outcome=RuleOutcome.FAIL,
        message=(
            f"Line items plus tax reconcile to {reconciled}, which does not "
            f"match the stated total of {extracted_voice.total_amount}"
        ),
    )


def check_currency_allowed(
    extracted_voice: ExtractedInvoice, config: RuleConfig, today: date
) -> RuleResult:
    """Flag a currency outside the configured allow-list, case-insensitively."""
    del today

    if extracted_voice.currency.strip().upper() in config.allowed_currencies:
        return RuleResult(
            rule_code=RuleCode.CURRENCY_ALLOWED,
            outcome=RuleOutcome.PASS,
        )

    allowed = ", ".join(sorted(config.allowed_currencies))
    return RuleResult(
        rule_code=RuleCode.CURRENCY_ALLOWED,
        outcome=RuleOutcome.FAIL,
        message=f"Currency {extracted_voice.currency} is not in the allowed set: {allowed}",
    )


def check_invoice_not_future(
    extracted_voice: ExtractedInvoice, config: RuleConfig, today: date
) -> RuleResult:
    """Flag an invoice dated after the evaluation date."""
    del config
    if extracted_voice.invoice_date <= today:
        return RuleResult(
            rule_code=RuleCode.INVOICE_DATE_NOT_IN_FUTURE,
            outcome=RuleOutcome.PASS,
        )
    return RuleResult(
        rule_code=RuleCode.INVOICE_DATE_NOT_IN_FUTURE,
        outcome=RuleOutcome.FAIL,
        message=f"Invoice date {extracted_voice.invoice_date} is after today ({today})",
    )


def check_invoice_submission_window(
    extracted_voice: ExtractedInvoice, config: RuleConfig, today: date
) -> RuleResult:
    """Flag an invoice older than the configured maximum submission age."""
    age_days = (today - extracted_voice.invoice_date).days
    if age_days <= config.max_expense_age_days:
        return RuleResult(
            rule_code=RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW,
            outcome=RuleOutcome.PASS,
        )
    return RuleResult(
        rule_code=RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW,
        outcome=RuleOutcome.FAIL,
        message=(
            f"Invoice is {age_days} days old, beyond the "
            f"{config.max_expense_age_days}-day submission window"
        ),
    )
