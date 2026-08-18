"""Rule codes and the always-present per-rule result each check returns."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.database.models.rule_result import RuleOutcome

__all__ = ["EvidenceValue", "RuleCode", "RuleOutcome", "RuleResult"]

type EvidenceValue = str | int | Decimal | date | UUID | Sequence[str]


class RuleCode(StrEnum):
    """Identify each deterministic policy rule the engine evaluates."""

    EXPENSE_WITHIN_AMOUNT_LIMIT = "expense_within_amount_limit"
    EXPENSE_WITHIN_SUBMISSION_WINDOW = "expense_within_submission_window"
    INVOICE_DATE_NOT_IN_FUTURE = "invoice_date_not_in_future"
    LINE_ITEM_TOTAL_CONSISTENCY = "line_item_total_consistency"
    CURRENCY_ALLOWED = "currency_allowed"


@dataclass(frozen=True)
class RuleResult:
    """One rule's outcome for one evaluated invoice."""

    rule_code: RuleCode
    outcome: RuleOutcome
    evidence: dict[str, EvidenceValue] = field(default_factory=dict)
