"""Specify how per-case results roll up into run totals and dimension slices."""

import pytest

from eval.explanation.score.aggregate import aggregate
from eval.explanation.score.results import (
    CaseResult,
    CheckResult,
    CheckScore,
    CitationScore,
    JudgeResult,
    JudgeScore,
)

pytestmark = pytest.mark.unit


def _check(check_id: str, *, passed: bool) -> CheckResult:
    return CheckResult(id=check_id, kind="must_contain", pattern="x", passed=passed)


def _judge(*, must_passed: bool, should_passed: bool = True) -> JudgeScore:
    return JudgeScore(
        results=[
            JudgeResult(
                id="answers_this_flag",
                severity="must",
                passed=must_passed,
                reason="r",
            ),
            JudgeResult(
                id="neutral_tone",
                severity="should",
                passed=should_passed,
                reason="r",
            ),
        ]
    )


def _scored(
    name: str,
    dimensions: list[str],
    *,
    recall: float,
    precision: float,
    spurious: int,
    deterministic_pass: bool,
    out_of_range: tuple[int, ...] = (),
    checks: list[CheckResult] | None = None,
    judge: JudgeScore | None = None,
) -> CaseResult:
    judge = judge or _judge(must_passed=deterministic_pass)
    return CaseResult(
        name=name,
        dimensions=tuple(dimensions),
        error=None,
        narrative="n",
        raw_indexes=(0,),
        cited_ids=("air#0",),
        out_of_range=out_of_range,
        citation=CitationScore(
            recall=recall,
            precision=precision,
            spurious=spurious,
            gate=deterministic_pass,
        ),
        check=CheckScore(results=checks or []),
        judge=judge,
        deterministic_pass=deterministic_pass,
        full_pass=deterministic_pass and judge.gate,
        latency_ms=5,
    )


@pytest.fixture
def results() -> list[CaseResult]:
    clean = _scored(
        "a_clean",
        ["clean-passage"],
        recall=1.0,
        precision=1.0,
        spurious=0,
        deterministic_pass=True,
        checks=[_check("names_window", passed=True)],
    )
    spurious = _scored(
        "b_spurious",
        ["clean-passage", "distractor-heavy"],
        recall=1.0,
        precision=0.5,
        spurious=1,
        deterministic_pass=False,
        checks=[_check("names_window", passed=False)],
    )
    errored = CaseResult.errored(
        "c_errored", ["distractor-heavy"], "model returned no JSON", latency_ms=9
    )
    return [clean, spurious, errored]


def should_count_cases_errors_and_deterministic_passes(
    results: list[CaseResult],
) -> None:
    totals = aggregate(results)

    assert totals.cases == 3
    assert totals.errored == 1
    assert totals.scored == 2
    assert totals.deterministic_pass == 1
    assert totals.deterministic_pass_rate == pytest.approx(0.3333)
    assert totals.error_rate == pytest.approx(0.3333)


def should_average_precision_and_recall_over_scored_cases_only(
    results: list[CaseResult],
) -> None:
    totals = aggregate(results)

    assert totals.mean_recall == pytest.approx(1.0)
    assert totals.mean_precision == pytest.approx(0.75)


def should_rate_spurious_and_out_of_range_over_every_case(
    results: list[CaseResult],
) -> None:
    totals = aggregate(results)

    assert totals.spurious_cases == 1
    assert totals.spurious_rate == pytest.approx(0.3333)
    assert totals.out_of_range_cases == 0
    assert totals.out_of_range_rate == pytest.approx(0.0)


def should_tally_each_check_over_the_cases_that_carry_it(
    results: list[CaseResult],
) -> None:
    totals = aggregate(results)

    names_window = totals.per_check["names_window"]
    assert names_window.passed == 1
    assert names_window.total == 2
    assert names_window.rate == pytest.approx(0.5)


def should_count_full_passes_over_every_case(results: list[CaseResult]) -> None:
    totals = aggregate(results)

    assert totals.full_pass == 1
    assert totals.full_pass_rate == pytest.approx(0.3333)


def should_tally_must_and_should_statements_separately(
    results: list[CaseResult],
) -> None:
    totals = aggregate(results)

    must = totals.per_must["answers_this_flag"]
    assert must.passed == 1
    assert must.total == 2

    should = totals.per_should["neutral_tone"]
    assert should.passed == 2
    assert should.total == 2
    assert "neutral_tone" not in totals.per_must


def should_slice_each_dimension_over_exactly_its_tagged_cases(
    results: list[CaseResult],
) -> None:
    totals = aggregate(results)

    clean = totals.by_dimension["clean-passage"]
    assert clean.cases == 2
    assert clean.deterministic_pass == 1
    assert clean.errored == 0

    distractor = totals.by_dimension["distractor-heavy"]
    assert distractor.cases == 2
    assert distractor.errored == 1
    assert distractor.scored == 1


def should_omit_dimensions_no_case_carries(results: list[CaseResult]) -> None:
    totals = aggregate(results)

    assert set(totals.by_dimension) == {"clean-passage", "distractor-heavy"}


def should_return_zero_rates_for_an_empty_run() -> None:
    totals = aggregate([])

    assert totals.cases == 0
    assert totals.error_rate == 0.0
    assert totals.deterministic_pass_rate == 0.0
    assert totals.full_pass_rate == 0.0
    assert totals.spurious_rate == 0.0
    assert totals.out_of_range_rate == 0.0
    assert totals.mean_precision == 0.0
    assert totals.mean_recall == 0.0
    assert totals.per_check == {}
    assert totals.per_must == {}
    assert totals.per_should == {}
    assert totals.by_dimension == {}
