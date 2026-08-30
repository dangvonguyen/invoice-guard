"""Pure roll-up of per-case results into run totals and per-dimension slices."""

from collections.abc import Iterable, Sequence
from statistics import fmean
from typing import Protocol

from eval._common.score.constants import RATE_DECIMALS
from eval._common.score.dimensions import dimension_tags
from eval.explanation.score.results import CaseResult, RunTally, Tally, Totals


class _IdVerdict(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def passed(self) -> bool: ...


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
    return _tally_by_id(
        check for r in results if r.check is not None for check in r.check.results
    )


def _per_rubric(results: Sequence[CaseResult], severity: str) -> dict[str, Tally]:
    return _tally_by_id(
        verdict
        for r in results
        if r.judge is not None
        for verdict in r.judge.results
        if verdict.severity == severity
    )


def _tally_by_id(verdicts: Iterable[_IdVerdict]) -> dict[str, Tally]:
    """Group pass/total counts by verdict ``id``, in first-seen order."""
    materialized = list(verdicts)
    tallies: dict[str, Tally] = {}
    for vid in dict.fromkeys(v.id for v in materialized):
        present = [v for v in materialized if v.id == vid]
        tallies[vid] = Tally(
            passed=sum(1 for v in present if v.passed), total=len(present)
        )
    return tallies


def _mean(values: Iterable[float]) -> float:
    data = list(values)
    if not data:
        return 0.0
    return round(fmean(data), RATE_DECIMALS)
