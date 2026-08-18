"""Project persisted rule results into reviewer-visible review flags."""

from dataclasses import dataclass
from typing import Any

from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.services.rules.result import RuleCode

_SUMMARIES: dict[tuple[RuleCode, RuleOutcome], str] = {
    (
        RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
        RuleOutcome.FAIL,
    ): "Invoice total exceeds the configured review limit.",
    (
        RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
        RuleOutcome.FAIL,
    ): "Line items and tax do not reconcile with the stated total.",
    (
        RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
        RuleOutcome.NOT_APPLICABLE,
    ): "No line items were extracted to reconcile against the total.",
    (
        RuleCode.CURRENCY_ALLOWED,
        RuleOutcome.FAIL,
    ): "Invoice currency is not in the allowed set.",
    (
        RuleCode.INVOICE_DATE_NOT_IN_FUTURE,
        RuleOutcome.FAIL,
    ): "Invoice is dated in the future.",
    (
        RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW,
        RuleOutcome.FAIL,
    ): "Invoice was submitted after the allowed submission window.",
}


def summary_for(rule_code: RuleCode, outcome: RuleOutcome) -> str | None:
    return _SUMMARIES.get((rule_code, outcome))


@dataclass(frozen=True)
class ReviewFlag:
    """One reviewer-visible condition produced by analysis."""

    code: str
    summary: str
    evidence: dict[str, Any]


def to_review_flags(results: list[InvoiceRuleResult]) -> list[ReviewFlag]:
    """Project an invoice's persisted rule results into its review flags."""
    flags = []
    for result in results:
        if result.outcome != RuleOutcome.FAIL:
            continue
        rule_code = RuleCode(result.rule_code)
        summary = summary_for(rule_code, result.outcome) or f"{rule_code.value} failed."
        flags.append(
            ReviewFlag(code=result.rule_code, summary=summary, evidence=result.evidence)
        )
    return flags
