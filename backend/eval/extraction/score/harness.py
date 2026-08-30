"""Drive the production extraction pipeline over selected cases and write the run artifacts."""

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.model import ExtractedInvoice, build_model_client
from app.services.extraction.pipeline import ExtractionPipeline
from eval._common.score import gitmeta
from eval._common.score.harness_support import (
    ABORTING_ERRORS,
    ScoringError,
    elapsed_ms,
    selector,
)
from eval.extraction import paths
from eval.extraction.score.aggregate import aggregate
from eval.extraction.score.artifacts import append_history_line, write_run_file
from eval.extraction.score.compare import compare_case
from eval.extraction.score.results import CaseScore, RunConfig, RunReport


@dataclass(frozen=True)
class _LoadedCase:
    name: str
    dimensions: tuple[str, ...]
    document_text: str
    expected: ExtractedInvoice


async def run(
    *,
    config: RunConfig,
    names: Sequence[str],
    dimensions: Sequence[str],
) -> tuple[RunReport, Path]:
    """Score the selected cases, write the run dump, and (whole-set only) history."""
    git_commit = gitmeta.head_commit()
    git_dirty = gitmeta.is_dirty()

    cases = _select_cases(paths.CASES_DIR, names, dimensions)
    if not cases:
        raise ScoringError("no cases matched the selection")

    pipeline = ExtractionPipeline(
        model=build_model_client(
            provider=config.provider,
            model=config.model,
            max_tokens=config.max_tokens,
        ),
        grounding_checker=GroundingChecker(),
    )
    semaphore = asyncio.Semaphore(config.concurrency)
    scores = list(
        await asyncio.gather(
            *(_score_case(case, pipeline, semaphore) for case in cases)
        )
    )

    report = RunReport(
        config=config,
        timestamp=datetime.now(UTC),
        git_commit=git_commit,
        git_dirty=git_dirty,
        selector=selector(names, dimensions),
        cases=scores,
        totals=aggregate(scores),
    )
    run_path = write_run_file(report, paths.RUNS_DIR)
    if report.selector is None:
        append_history_line(report, paths.HISTORY_PATH, run_file=run_path.name)
    return report, run_path


def _select_cases(
    cases_dir: Path, names: Sequence[str], dimensions: Sequence[str]
) -> list[_LoadedCase]:
    try:
        case_dirs = sorted(p for p in cases_dir.iterdir() if p.is_dir())
    except OSError as exc:
        raise ScoringError(f"cannot read cases directory {cases_dir}: {exc}") from exc

    cases = [_load_case(p) for p in case_dirs]
    if names:
        by_name = {case.name: case for case in cases}
        unknown = [name for name in names if name not in by_name]
        if unknown:
            raise ScoringError(f"unknown case(s): {', '.join(sorted(unknown))}")
        return [by_name[name] for name in names]
    if dimensions:
        wanted = set(dimensions)
        return [case for case in cases if wanted.intersection(case.dimensions)]
    return cases


def _load_case(case_dir: Path) -> _LoadedCase:
    try:
        meta = yaml.safe_load((case_dir / paths.CASE_YAML).read_text()) or {}
        expected = ExtractedInvoice.model_validate_json(
            (case_dir / paths.EXPECTED_JSON).read_text()
        )
        document_text = (case_dir / paths.SOURCE_EXTRACTED_TXT).read_text()
    except (OSError, ValueError) as exc:
        raise ScoringError(f"malformed case {case_dir.name}: {exc}") from exc
    return _LoadedCase(
        name=case_dir.name,
        dimensions=tuple(meta.get("dimensions") or []),
        document_text=document_text,
        expected=expected,
    )


async def _score_case(
    case: _LoadedCase, pipeline: ExtractionPipeline, semaphore: asyncio.Semaphore
) -> CaseScore:
    async with semaphore:
        start = time.perf_counter()
        try:
            result = await pipeline.run(document_text=case.document_text)
        except ABORTING_ERRORS as exc:
            raise ScoringError(f"provider unavailable: {exc}") from exc
        except Exception as exc:  # a measured outcome, not an operational failure
            return CaseScore.errored(
                case.name,
                case.dimensions,
                str(exc),
                latency_ms=elapsed_ms(start),
                expected_line_count=len(case.expected.line_items),
            )
    return compare_case(
        case.expected,
        result.fields,
        name=case.name,
        dimensions=case.dimensions,
        confidence=result.confidence,
        confidence_reason=result.confidence_reason,
        latency_ms=elapsed_ms(start),
    )


def format_summary(report: RunReport, run_path: Path) -> str:
    """The run aggregates and per-field accuracy table, for stdout."""
    totals = report.totals
    lines = [
        f"scored {totals.cases} case(s) via {report.config.provider}/{report.config.model}",
        f"  fully correct : {totals.fully_correct}/{totals.cases} ({totals.fully_correct_rate})",
        f"  errored       : {totals.error_count}/{totals.cases} ({totals.error_rate})",
    ]
    for field, tally in totals.field_accuracy.items():
        lines.append(f"  {field:<21}: {tally.correct}/{tally.total} ({tally.rate})")
    lines.append(f"run file: {run_path}")
    return "\n".join(lines)
