"""Project persisted rule results into reviewer-visible review flags."""

from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.schemas.review import ReviewFlagView
from app.services.rules.definitions import RULES
from app.services.rules.result import RuleCode

_SUMMARIES: dict[tuple[RuleCode, RuleOutcome], str] = {
    (rule.code, outcome): summary
    for rule in RULES
    for outcome, summary in rule.summaries.items()
}


def summary_for(rule_code: RuleCode, outcome: RuleOutcome) -> str | None:
    return _SUMMARIES.get((rule_code, outcome))


def to_review_flags(results: list[InvoiceRuleResult]) -> list[ReviewFlagView]:
    """Project an invoice's persisted rule results into its review flags."""
    flags = []
    for result in results:
        if result.outcome != RuleOutcome.FAIL:
            continue
        rule_code = RuleCode(result.rule_code)
        summary = summary_for(rule_code, result.outcome) or f"{rule_code.value} failed."
        flags.append(
            ReviewFlagView(
                code=result.rule_code, summary=summary, evidence=result.evidence
            )
        )
    return flags
