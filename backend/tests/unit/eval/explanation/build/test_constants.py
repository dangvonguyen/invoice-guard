"""Pin the build's frozen vocab against its production sources of truth."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.database.models.rule_result import RuleOutcome
from app.services.extraction.model import ExtractedInvoice
from app.services.rules.checks import (
    check_currency_allowed,
    check_invoice_submission_window,
    check_max_expense_amount,
)
from app.services.rules.config import RuleConfig
from app.services.rules.result import RuleCode
from eval.explanation.build.constants import CHUNKER, EVIDENCE_KEYS

pytestmark = pytest.mark.unit

_CONFIG = RuleConfig(
    max_expense_amount=Decimal("100.00"),
    max_expense_age_days=30,
    allowed_currencies=frozenset({"USD"}),
    reconciliation_tolerance=Decimal("0.01"),
)
_TODAY = date(2024, 6, 1)


def _invoice(**overrides: object) -> ExtractedInvoice:
    base = {
        "vendor_name": "Vendor",
        "invoice_date": "2024-05-15",
        "total_amount": "50.00",
        "currency": "USD",
    }
    return ExtractedInvoice.model_validate({**base, **overrides})


def should_match_the_production_ingestion_defaults_for_chunker_params() -> None:
    assert {
        "min_tokens": Settings.model_fields["POLICY_CHUNK_MIN_TOKENS"].default,
        "max_tokens": Settings.model_fields["POLICY_CHUNK_MAX_TOKENS"].default,
    } == CHUNKER


def should_pin_the_amount_limit_evidence_keys_to_what_the_check_emits() -> None:
    result = check_max_expense_amount(
        _invoice(total_amount="500.00", currency="EUR"), _CONFIG, _TODAY
    )

    assert result.outcome is RuleOutcome.FAIL
    assert result.evidence.keys() == EVIDENCE_KEYS[RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT]


def should_pin_the_currency_evidence_keys_to_what_the_check_emits() -> None:
    result = check_currency_allowed(_invoice(currency="JPY"), _CONFIG, _TODAY)

    assert result.outcome is RuleOutcome.FAIL
    assert result.evidence.keys() == EVIDENCE_KEYS[RuleCode.CURRENCY_ALLOWED]


def should_pin_the_submission_window_evidence_keys_to_what_the_check_emits() -> None:
    result = check_invoice_submission_window(
        _invoice(invoice_date="2024-01-01"), _CONFIG, _TODAY
    )

    assert result.outcome is RuleOutcome.FAIL
    assert (
        result.evidence.keys()
        == EVIDENCE_KEYS[RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW]
    )
