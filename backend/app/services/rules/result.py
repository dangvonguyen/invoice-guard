"""Rule codes and the always-present per-rule result each check returns."""

from dataclasses import dataclass
from enum import StrEnum


class RuleCode(StrEnum):
    """Identify each deterministic policy rule the engine evaluates."""

    EXPENSE_WITHIN_AMOUNT_LIMIT = "expense_within_amount_limit"


class RuleOutcome(StrEnum):
    """The result of evaluating one deterministic rule against one invoice."""

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class RuleResult:
    """One rule's outcome for one evaluated invoice."""

    rule_code: RuleCode
    outcome: RuleOutcome
    message: str | None = None
