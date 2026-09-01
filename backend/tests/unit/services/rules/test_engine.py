"""Specify how the rule engine orchestrates the full, fixed set of checks."""

import pytest

from app.database.models.rule_result import RuleOutcome
from app.services.rules.definitions import RuleDefinition
from app.services.rules.engine import RuleEngine
from app.services.rules.result import RuleCode, RuleResult
from tests.support.constants import COMPLIANT_INVOICE, RULE_CONFIG, TODAY

pytestmark = pytest.mark.unit


def should_return_exactly_one_result_per_configured_rule_code() -> None:
    """Never return a variable-length list of only the broken rules."""
    engine = RuleEngine(config=RULE_CONFIG)

    results = engine.evaluate(COMPLIANT_INVOICE, TODAY)

    assert {result.rule_code for result in results} == set(RuleCode)
    assert len(results) == len(RuleCode)


def should_be_pure_returning_the_same_result_for_the_same_input() -> None:
    """Produce identical results for identical fields and evaluation date."""
    engine = RuleEngine(config=RULE_CONFIG)

    first = engine.evaluate(COMPLIANT_INVOICE, TODAY)
    second = engine.evaluate(COMPLIANT_INVOICE, TODAY)

    assert first == second


def should_evaluate_using_the_injected_rule_definitions_table() -> None:
    """The engine runs whatever `RuleDefinition`s it is given, not a hardcoded list."""
    stub_result = RuleResult(
        rule_code=RuleCode.CURRENCY_ALLOWED, outcome=RuleOutcome.PASS
    )
    stub_rule = RuleDefinition(
        code=RuleCode.CURRENCY_ALLOWED,
        check=lambda *_args: stub_result,
    )
    engine = RuleEngine(config=RULE_CONFIG, rules=(stub_rule,))

    results = engine.evaluate(COMPLIANT_INVOICE, TODAY)

    assert results == [stub_result]
