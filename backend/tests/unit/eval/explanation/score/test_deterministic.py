"""Specify the pure deterministic scorer: cite mapping, metrics, checks, verdict."""

import pytest

from eval.explanation.build.casefile import Check, Citations, Grading
from eval.explanation.score.deterministic import (
    citation_score,
    map_cited_indexes,
    run_checks,
    score_case,
)

pytestmark = pytest.mark.unit

_CONTEXT = ("air#0", "lodging#0", "meals#0")


def _grading(
    *,
    ideal: list[str],
    min_recall: float = 1.0,
    max_spurious: int = 0,
    checks: list[Check] | None = None,
) -> Grading:
    return Grading(
        citations=Citations(
            ideal=ideal, min_recall=min_recall, max_spurious=max_spurious
        ),
        checks=checks or [],
        rubric=[],
    )


def should_map_indexes_to_context_ids_deduped_in_first_seen_order() -> None:
    mapping = map_cited_indexes([2, 0, 0, 2], _CONTEXT)

    assert mapping.cited_ids == ("meals#0", "air#0")
    assert mapping.out_of_range == ()


def should_flag_negative_and_overflow_indexes_as_out_of_range() -> None:
    mapping = map_cited_indexes([-1, 3, 3, 1], _CONTEXT)

    assert mapping.cited_ids == ("lodging#0",)
    assert mapping.out_of_range == (-1, 3)


def should_compute_recall_over_the_ideal_set() -> None:
    score = citation_score(
        ["air#0"],
        ["air#0", "lodging#0"],
        min_recall=1.0,
        max_spurious=0,
        out_of_range=False,
    )

    assert score.recall == pytest.approx(0.5)


def should_treat_empty_ideal_as_full_recall() -> None:
    score = citation_score([], [], min_recall=1.0, max_spurious=0, out_of_range=False)

    assert score.recall == pytest.approx(1.0)


def should_count_spurious_cites_outside_the_ideal_set() -> None:
    score = citation_score(
        ["air#0", "lodging#0", "meals#0"],
        ["air#0"],
        min_recall=1.0,
        max_spurious=0,
        out_of_range=False,
    )

    assert score.spurious == 2
    assert score.precision == pytest.approx(1 / 3)
    assert score.gate is False


def should_report_full_precision_when_nothing_was_cited() -> None:
    score = citation_score(
        [], ["air#0"], min_recall=0.0, max_spurious=0, out_of_range=False
    )

    assert score.precision == pytest.approx(1.0)


def should_pass_the_citation_gate_only_when_recall_and_spurious_are_in_bounds() -> None:
    passing = citation_score(
        ["air#0"],
        ["air#0"],
        min_recall=1.0,
        max_spurious=0,
        out_of_range=False,
    )
    short_recall = citation_score(
        ["air#0"],
        ["air#0", "lodging#0"],
        min_recall=1.0,
        max_spurious=5,
        out_of_range=False,
    )

    assert passing.gate is True
    assert short_recall.gate is False


def should_hard_fail_the_gate_on_any_out_of_range_index_regardless_of_slack() -> None:
    score = citation_score(
        [],
        [],
        min_recall=0.0,
        max_spurious=99,
        out_of_range=True,
    )

    assert score.recall == pytest.approx(1.0)
    assert score.spurious == 0
    assert score.gate is False


def should_match_must_contain_and_must_absent_case_insensitively() -> None:
    checks = [
        Check(id="names_window", kind="must_contain", pattern=r"30\s*days"),
        Check(id="no_deadline", kind="must_absent", pattern=r"deadline"),
    ]

    score = run_checks(checks, "Submitted 30 DAYS after the trip; missed the DEADLINE.")

    assert score.results[0].passed is True
    assert score.results[1].passed is False
    assert score.gate is False


def should_and_the_citation_gate_with_every_check_for_the_verdict() -> None:
    checks = [Check(id="names_window", kind="must_contain", pattern=r"30\s*days")]

    citing_but_silent = score_case(
        narrative="The invoice was simply too old.",
        raw_indexes=[0],
        context=_CONTEXT,
        grading=_grading(ideal=["air#0"], checks=checks),
    )
    citing_and_naming = score_case(
        narrative="Filed more than 30 days after the expense.",
        raw_indexes=[0],
        context=_CONTEXT,
        grading=_grading(ideal=["air#0"], checks=checks),
    )

    assert citing_but_silent.citation.gate is True
    assert citing_but_silent.passed is False
    assert citing_and_naming.passed is True


def should_hard_fail_the_verdict_when_an_index_is_out_of_range() -> None:
    result = score_case(
        narrative="anything",
        raw_indexes=[9],
        context=_CONTEXT,
        grading=_grading(ideal=[], min_recall=0.0, max_spurious=99),
    )

    assert result.out_of_range == (9,)
    assert result.passed is False
