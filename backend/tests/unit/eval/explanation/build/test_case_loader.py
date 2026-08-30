"""Specify the ``case.yaml`` loader and every build-abort condition it enforces."""

from typing import Any

import pytest

from app.services.rules.result import RuleCode
from eval.explanation.build.casefile import CaseFile, load_case
from eval.explanation.build.chunking import IdentifiedChunk

pytestmark = pytest.mark.unit


def _chunks(*ids: str) -> list[IdentifiedChunk]:
    return [
        IdentifiedChunk(id=cid, label=cid.split("#")[0], content=f"body of {cid}")
        for cid in ids
    ]


_AMOUNT_LIMIT_CONTEXT = (
    "3 Air Travel#0",
    "2 Lodging#0",
    "5 Non-Reimbursable Expenses#0",
)


def _amount_limit_case(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Airfare over the prior-approval threshold, USD invoice",
        "rule": "EXPENSE_WITHIN_AMOUNT_LIMIT",
        "dimensions": ["threshold-in-prose", "distractor-heavy"],
        "evidence": {
            "invoice_total": "920.00",
            "max_expense_amount": "700.00",
            "currency": "USD",
        },
        "context": list(_AMOUNT_LIMIT_CONTEXT),
        "grading": {
            "citations": {
                "ideal": ["3 Air Travel#0"],
                "min_recall": 1.0,
                "max_spurious": 0,
            },
            "checks": [
                {
                    "id": "names_threshold",
                    "kind": "must_contain",
                    "pattern": r"(?<![\d.])700(?![\d.])",
                },
                {
                    "id": "no_deadline_leak",
                    "kind": "must_absent",
                    "pattern": "15 days|30 days|deadline",
                },
            ],
            "rubric": [
                {
                    "id": "answers_this_flag",
                    "severity": "must",
                    "statement": "Attributes the flag to airfare exceeding the threshold.",
                },
                {
                    "id": "neutral_tone",
                    "severity": "should",
                    "statement": "Tone is neutral and professional.",
                },
            ],
        },
        "notes": "Distractor-heavy amount-limit case.",
    }
    base.update(overrides)
    return base


def _amount_limit_chunks() -> list[IdentifiedChunk]:
    return _chunks(*_AMOUNT_LIMIT_CONTEXT, "6 Expense Reimbursement Timelines#1")


def should_load_a_valid_case_into_a_casefile() -> None:
    case = load_case(_amount_limit_case(), _amount_limit_chunks())

    assert isinstance(case, CaseFile)
    assert case.rule is RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT
    assert [c.id for c in case.grading.checks] == [
        "names_threshold",
        "no_deadline_leak",
    ]
    assert case.grading.citations.ideal == ["3 Air Travel#0"]


def should_derive_the_flag_summary_from_summary_for_at_load() -> None:
    case = load_case(_amount_limit_case(), _amount_limit_chunks())

    assert case.summary == "Invoice total exceeds the configured review limit."


def should_abort_when_the_rule_has_no_fail_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("eval.explanation.build.casefile.summary_for", lambda *_: None)

    with pytest.raises(ValueError, match="no FAIL summary"):
        load_case(_amount_limit_case(), _amount_limit_chunks())


def should_abort_when_two_chunks_resolve_to_the_same_id() -> None:
    collided = [*_amount_limit_chunks(), *_chunks("3 Air Travel#0")]

    with pytest.raises(ValueError, match="collision"):
        load_case(_amount_limit_case(), collided)


def should_abort_when_the_rule_is_not_a_rulecode() -> None:
    with pytest.raises(ValueError, match="not a RuleCode"):
        load_case(_amount_limit_case(rule="TOTALLY_MADE_UP"), _amount_limit_chunks())


def should_abort_when_the_rule_is_not_explainable() -> None:
    with pytest.raises(ValueError, match="Explainable"):
        load_case(
            _amount_limit_case(rule="INVOICE_DATE_NOT_IN_FUTURE"),
            _amount_limit_chunks(),
        )


def should_abort_when_a_context_id_is_absent_from_chunks_json() -> None:
    case = _amount_limit_case(
        context=[*_AMOUNT_LIMIT_CONTEXT, "9 Nonexistent Section#0"]
    )

    with pytest.raises(ValueError, match="context IDs absent"):
        load_case(case, _amount_limit_chunks())


def should_abort_when_evidence_keys_diverge_from_the_rule_contract() -> None:
    case = _amount_limit_case(evidence={"invoice_total": "920.00", "currency": "USD"})

    with pytest.raises(ValueError, match="evidence keys"):
        load_case(case, _amount_limit_chunks())


def should_abort_when_context_has_a_duplicate_id() -> None:
    case = _amount_limit_case(context=[*_AMOUNT_LIMIT_CONTEXT, "2 Lodging#0"])

    with pytest.raises(ValueError, match="duplicate"):
        load_case(case, _amount_limit_chunks())


def should_abort_when_ideal_citations_are_not_a_subset_of_context() -> None:
    grading = _amount_limit_case()["grading"]
    grading["citations"]["ideal"] = ["6 Expense Reimbursement Timelines#1"]

    with pytest.raises(ValueError, match="ideal citations"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


def should_abort_when_a_check_id_collides_with_a_rubric_id() -> None:
    grading = _amount_limit_case()["grading"]
    grading["rubric"][0]["id"] = "names_threshold"

    with pytest.raises(ValueError, match="id collision"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


def should_abort_when_a_check_pattern_does_not_compile() -> None:
    grading = _amount_limit_case()["grading"]
    grading["checks"][0]["pattern"] = "700(unclosed"

    with pytest.raises(ValueError, match="does not compile"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


def should_abort_when_a_check_kind_is_unknown() -> None:
    grading = _amount_limit_case()["grading"]
    grading["checks"][0]["kind"] = "must_maybe"

    with pytest.raises(ValueError, match="must_contain"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


def should_abort_when_a_rubric_severity_is_unknown() -> None:
    grading = _amount_limit_case()["grading"]
    grading["rubric"][0]["severity"] = "nice-to-have"

    with pytest.raises(ValueError, match="must"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


@pytest.mark.parametrize("bad_recall", [-0.1, 1.5])
def should_abort_when_min_recall_is_outside_the_unit_interval(
    bad_recall: float,
) -> None:
    grading = _amount_limit_case()["grading"]
    grading["citations"]["min_recall"] = bad_recall

    with pytest.raises(ValueError, match="min_recall"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


def should_abort_when_max_spurious_is_negative() -> None:
    grading = _amount_limit_case()["grading"]
    grading["citations"]["max_spurious"] = -1

    with pytest.raises(ValueError, match="max_spurious"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())


def should_abort_when_a_dimension_is_outside_the_closed_vocabulary() -> None:
    case = _amount_limit_case(dimensions=["threshold-in-prose", "made-up-tag"])

    with pytest.raises(ValueError, match="dimension"):
        load_case(case, _amount_limit_chunks())


def should_abort_when_a_case_carries_no_dimensions() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        load_case(_amount_limit_case(dimensions=[]), _amount_limit_chunks())


# --- hard-negative: the `hard-negative` dimension and an empty ideal must agree ---

_CURRENCY_HN_CONTEXT = (
    "6 Expense Reimbursement Timelines#0",
    "2 Lodging#0",
    "5 Non-Reimbursable Expenses#0",
)

_DECLINE_MUST = {
    "id": "declines",
    "severity": "must",
    "statement": "States that the policy does not address currency restrictions.",
}
_PLAIN_MUST = {
    "id": "grounded",
    "severity": "must",
    "statement": "Every factual claim is supported by the provided excerpts.",
}


def _currency_hn_case(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "EUR invoice; handbook is silent on currency",
        "rule": "CURRENCY_ALLOWED",
        "dimensions": ["hard-negative", "distractor-heavy"],
        "evidence": {"currency": "EUR", "allowed_currencies": ["USD"]},
        "context": list(_CURRENCY_HN_CONTEXT),
        "grading": {
            "citations": {"ideal": [], "min_recall": 1.0, "max_spurious": 0},
            "checks": [
                {
                    "id": "no_invented_rule",
                    "kind": "must_absent",
                    "pattern": "must be USD|USD only",
                }
            ],
            "rubric": [dict(_DECLINE_MUST), dict(_PLAIN_MUST)],
        },
        "notes": "Handbook says nothing about currency; the model must abstain.",
    }
    base.update(overrides)
    return base


def _currency_hn_chunks() -> list[IdentifiedChunk]:
    return _chunks(*_CURRENCY_HN_CONTEXT)


def should_load_a_valid_hard_negative_case() -> None:
    case = load_case(_currency_hn_case(), _currency_hn_chunks())

    assert case.grading.citations.ideal == []
    assert "hard-negative" in case.dimensions
    assert case.summary == "Invoice currency is not in the allowed set."


def should_abort_when_the_hard_negative_dimension_has_a_non_empty_ideal() -> None:
    grading = _currency_hn_case()["grading"]
    grading["citations"]["ideal"] = ["2 Lodging#0"]

    with pytest.raises(ValueError, match="hard-negative"):
        load_case(_currency_hn_case(grading=grading), _currency_hn_chunks())


def should_abort_when_an_empty_ideal_is_not_tagged_hard_negative() -> None:
    grading = _amount_limit_case()["grading"]
    grading["citations"]["ideal"] = []

    with pytest.raises(ValueError, match="hard-negative"):
        load_case(_amount_limit_case(grading=grading), _amount_limit_chunks())
