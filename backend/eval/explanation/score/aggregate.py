"""Pure roll-up of per-case results into run totals and per-dimension slices."""

from collections.abc import Iterable, Sequence
from statistics import fmean

from eval._common.score.constants import RATE_DECIMALS
from eval._common.score.dimensions import dimension_tags
from eval.explanation.score.results import (
    CaseResult,
    JudgeResult,
    RunTally,
    Tally,
    Totals,
)


def aggregate(results: Sequence[CaseResult]) -> Totals:
    """Return whole-run totals plus a :class:`RunTally` per dimension tag."""
    base = _tally(results)
    by_dimension = {
        tag: _tally([r for r in results if tag in r.dimensions])
        for tag in dimension_tags(results)
    }
    return Totals(
        cases=base.cases,
        errored=base.errored,
        scored=base.scored,
        deterministic_pass=base.deterministic_pass,
        full_pass=base.full_pass,
        spurious_cases=base.spurious_cases,
        out_of_range_cases=base.out_of_range_cases,
        mean_precision=base.mean_precision,
        mean_recall=base.mean_recall,
        per_check=base.per_check,
        per_must=base.per_must,
        per_should=base.per_should,
        by_dimension=by_dimension,
    )


def _tally(results: Sequence[CaseResult]) -> RunTally:
    scored = [r for r in results if not r.is_errored]
    citations = [r.citation for r in scored if r.citation is not None]
    return RunTally(
        cases=len(results),
        errored=len(results) - len(scored),
        scored=len(scored),
        deterministic_pass=sum(1 for r in results if r.deterministic_pass),
        full_pass=sum(1 for r in results if r.full_pass),
        spurious_cases=sum(1 for c in citations if c.spurious > 0),
        out_of_range_cases=sum(1 for r in results if r.out_of_range),
        mean_precision=_mean(c.precision for c in citations),
        mean_recall=_mean(c.recall for c in citations),
        per_check=_per_check(results),
        per_must=_per_rubric(results, "must"),
        per_should=_per_rubric(results, "should"),
    )


def _per_check(results: Sequence[CaseResult]) -> dict[str, Tally]:
    scored_checks = [c for r in results if r.check is not None for c in r.check.results]
    check_ids: dict[str, None] = {}
    for check in scored_checks:
        check_ids.setdefault(check.id, None)
    tallies: dict[str, Tally] = {}
    for check_id in check_ids:
        present = [c for c in scored_checks if c.id == check_id]
        tallies[check_id] = Tally(
            passed=sum(1 for c in present if c.passed), total=len(present)
        )
    return tallies


def _per_rubric(results: Sequence[CaseResult], severity: str) -> dict[str, Tally]:
    verdicts: list[JudgeResult] = [
        v
        for r in results
        if r.judge is not None
        for v in r.judge.results
        if v.severity == severity
    ]
    statement_ids: dict[str, None] = {}
    for verdict in verdicts:
        statement_ids.setdefault(verdict.id, None)
    tallies: dict[str, Tally] = {}
    for statement_id in statement_ids:
        present = [v for v in verdicts if v.id == statement_id]
        tallies[statement_id] = Tally(
            passed=sum(1 for v in present if v.passed), total=len(present)
        )
    return tallies


def _mean(values: Iterable[float]) -> float:
    data = list(values)
    if not data:
        return 0.0
    return round(fmean(data), RATE_DECIMALS)
