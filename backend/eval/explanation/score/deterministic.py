"""Pure, keyless deterministic scoring: cite mapping, citation metrics, checks.

Nothing here calls a model or touches the network. The harness owns the one
generation call; this module grades its output.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from eval.explanation.build.casefile import Check, Grading
from eval.explanation.score.results import CheckResult, CheckScore, CitationScore


@dataclass(frozen=True)
class CiteMapping:
    """The result of mapping raw model indexes onto ``context`` chunk IDs."""

    cited_ids: tuple[str, ...]
    out_of_range: tuple[int, ...]


@dataclass(frozen=True)
class DeterministicScore:
    """Everything the deterministic layer decides about one case."""

    cited_ids: tuple[str, ...]
    out_of_range: tuple[int, ...]
    citation: CitationScore
    check: CheckScore
    passed: bool


def map_cited_indexes(
    raw_indexes: Sequence[int], context: Sequence[str]
) -> CiteMapping:
    """Map each raw index to ``context[i]``; collect any out-of-range index.

    Both lists are deduplicated with first-seen order preserved. An index is
    out of range when ``i < 0`` or ``i >= len(context)``.
    """
    cited_ids: list[str] = []
    out_of_range: list[int] = []
    for index in raw_indexes:
        if index < 0 or index >= len(context):
            if index not in out_of_range:
                out_of_range.append(index)
            continue
        chunk_id = context[index]
        if chunk_id not in cited_ids:
            cited_ids.append(chunk_id)
    return CiteMapping(tuple(cited_ids), tuple(out_of_range))


def citation_score(
    cited_ids: Sequence[str],
    ideal: Sequence[str],
    *,
    min_recall: float,
    max_spurious: int,
    out_of_range: bool,
) -> CitationScore:
    """Recall / spurious / precision plus the citation gate.

    ``recall`` is ``1.0`` when ``ideal`` is empty; ``precision`` is ``1.0`` when
    nothing was cited. Any out-of-range index fails the gate unconditionally.
    """
    cited = set(cited_ids)
    wanted = set(ideal)
    hits = cited & wanted

    recall = 1.0 if not wanted else len(hits) / len(wanted)
    precision = 1.0 if not cited else len(hits) / len(cited)
    spurious = len(cited - wanted)

    gate = not out_of_range and recall >= min_recall and spurious <= max_spurious
    return CitationScore(
        recall=recall,
        precision=precision,
        spurious=spurious,
        gate=gate,
    )


def run_checks(checks: Sequence[Check], narrative: str) -> CheckScore:
    """Evaluate every ``must_contain`` / ``must_absent`` check against ``narrative``."""
    results: list[CheckResult] = []
    for check in checks:
        found = re.search(check.pattern, narrative, re.IGNORECASE) is not None
        passed = found if check.kind == "must_contain" else not found
        results.append(
            CheckResult(
                id=check.id,
                kind=check.kind,
                pattern=check.pattern,
                passed=passed,
            )
        )
    return CheckScore(results=results)


def score_case(
    *,
    narrative: str,
    raw_indexes: Sequence[int],
    context: Sequence[str],
    grading: Grading,
) -> DeterministicScore:
    """The deterministic verdict = citation gate AND every check passing."""
    mapping = map_cited_indexes(raw_indexes, context)
    citation = citation_score(
        mapping.cited_ids,
        grading.citations.ideal,
        min_recall=grading.citations.min_recall,
        max_spurious=grading.citations.max_spurious,
        out_of_range=bool(mapping.out_of_range),
    )
    check = run_checks(grading.checks, narrative)
    passed = citation.gate and check.gate
    return DeterministicScore(
        cited_ids=mapping.cited_ids,
        out_of_range=mapping.out_of_range,
        citation=citation,
        check=check,
        passed=passed,
    )
