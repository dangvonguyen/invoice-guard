"""Specify the invariants of the single rule-definitions table.

The engine and the reviewer-facing flag summaries both read from `RULES`, so
these tests guard the property that adding a rule means adding one entry
here rather than touching several files that would otherwise drift out of
sync.
"""

import pytest

from app.database.models.rule_result import RuleOutcome
from app.services.rules.definitions import RULES
from app.services.rules.result import RuleCode
from tests.support.constants import COMPLIANT_INVOICE, RULE_CONFIG, TODAY

pytestmark = pytest.mark.unit


def should_define_exactly_one_entry_per_rule_code() -> None:
    """No rule code is missing from, or duplicated in, the definitions table."""
    codes = [rule.code for rule in RULES]

    assert set(codes) == set(RuleCode)
    assert len(codes) == len(set(codes))


def should_register_a_fail_summary_for_every_rule() -> None:
    """Every rule has reviewer-facing text for the outcome that flags it."""
    for rule in RULES:
        assert RuleOutcome.FAIL in rule.summaries


def should_run_the_check_registered_under_its_own_rule_code() -> None:
    """A definition's `check` must self-report the same code it is filed under.

    Guards against a mismatched pairing (a table entry wired to the wrong
    check function) type-checking cleanly but flagging the wrong rule.
    """
    for rule in RULES:
        result = rule.check(COMPLIANT_INVOICE, RULE_CONFIG, TODAY)
        assert result.rule_code == rule.code
