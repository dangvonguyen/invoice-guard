"""Drive the generation client over selected cases and write the run artifacts.

The harness deliberately bypasses ``ExplanationService.resolve`` and
``_verify_citations``: it calls the generation client directly and hands the raw
``cited_chunk_indexes`` to :mod:`deterministic`, which does its own stricter
cite mapping.
"""

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from anthropic import APIConnectionError as _AnthropicConnError
from anthropic import AuthenticationError as _AnthropicAuthError
from openai import APIConnectionError as _OpenAIConnError
from openai import AuthenticationError as _OpenAIAuthError

from app.services.explanations.generation import (
    GenerationClient,
    build_generation_client,
)
from eval import gitmeta
from eval.explanation import paths
from eval.explanation.build.casefile import CaseFile, iter_case_dirs, load_case_dir
from eval.explanation.build.chunking import IdentifiedChunk, read_chunks
from eval.explanation.build.prompts import resolve_context
from eval.explanation.score.aggregate import aggregate
from eval.explanation.score.artifacts import append_history_if_whole_set, write_run_file
from eval.explanation.score.deterministic import score_case
from eval.explanation.score.judge import JudgeClient, build_judge_client, to_judge_score
from eval.explanation.score.results import CaseResult, RunConfig, RunReport

# Provider errors that mean no case can succeed — abort the whole run.
_ABORTING_ERRORS = (
    _OpenAIAuthError,
    _OpenAIConnError,
    _AnthropicAuthError,
    _AnthropicConnError,
)


class ScoringError(RuntimeError):
    """An operational failure that aborts the run before any artifact is written."""


@dataclass(frozen=True)
class _LoadedCase:
    name: str
    dimensions: tuple[str, ...]
    case: CaseFile


async def run(
    *,
    config: RunConfig,
    names: Sequence[str],
    dimensions: Sequence[str],
) -> tuple[RunReport, Path]:
    """Score the selected cases, write the run dump, and (whole-set only) history."""
    git_commit = gitmeta.head_commit()
    git_dirty = gitmeta.is_dirty()

    chunks = read_chunks(paths.CHUNKS_JSON)
    cases = _select_cases(chunks, names, dimensions)
    if not cases:
        raise ScoringError("no cases matched the selection")

    client = build_generation_client(
        provider=config.provider,
        model=config.model,
        max_tokens=config.max_tokens,
    )
    judge_client = build_judge_client(
        provider=config.judge_provider,
        model=config.judge_model,
        max_tokens=config.judge_max_tokens,
    )
    semaphore = asyncio.Semaphore(config.concurrency)
    results = list(
        await asyncio.gather(
            *(
                _score_case(case, chunks, client, judge_client, semaphore)
                for case in cases
            )
        )
    )

    report = RunReport(
        config=config,
        timestamp=datetime.now(UTC),
        git_commit=git_commit,
        git_dirty=git_dirty,
        selector=_selector(names, dimensions),
        cases=results,
        totals=aggregate(results),
    )
    run_path = write_run_file(report, paths.RUNS_DIR)
    append_history_if_whole_set(report, paths.HISTORY_PATH, run_file=run_path.name)
    return report, run_path


def _selector(
    names: Sequence[str], dimensions: Sequence[str]
) -> dict[str, list[str]] | None:
    """The report's record of how this run was narrowed, or ``None`` for a bare run."""
    if names:
        return {"names": list(names)}
    if dimensions:
        return {"dimensions": list(dimensions)}
    return None


def _select_cases(
    chunks: Sequence[IdentifiedChunk],
    names: Sequence[str],
    dimensions: Sequence[str],
) -> list[_LoadedCase]:
    try:
        case_dirs = iter_case_dirs()
    except OSError as exc:
        raise ScoringError(f"cannot read cases directory: {exc}") from exc

    loaded = [_load_case(case_dir, chunks) for case_dir in case_dirs]
    if names:
        by_name = {case.name: case for case in loaded}
        unknown = [name for name in names if name not in by_name]
        if unknown:
            raise ScoringError(f"unknown case(s): {', '.join(sorted(unknown))}")
        return [by_name[name] for name in names]
    if dimensions:
        wanted = set(dimensions)
        return [case for case in loaded if wanted.intersection(case.dimensions)]
    return loaded


def _load_case(case_dir: Path, chunks: Sequence[IdentifiedChunk]) -> _LoadedCase:
    try:
        case = load_case_dir(case_dir, list(chunks))
    except (OSError, ValueError) as exc:
        raise ScoringError(f"malformed case {case_dir.name}: {exc}") from exc
    return _LoadedCase(
        name=case_dir.name,
        dimensions=tuple(case.dimensions),
        case=case,
    )


async def _score_case(
    loaded: _LoadedCase,
    chunks: Sequence[IdentifiedChunk],
    client: GenerationClient,
    judge_client: JudgeClient,
    semaphore: asyncio.Semaphore,
) -> CaseResult:
    case = loaded.case
    resolved_chunks = resolve_context(case.context, list(chunks))
    async with semaphore:
        start = time.perf_counter()
        try:
            generated = await client.generate_explanation(
                summary=case.summary,
                evidence=dict(case.evidence),
                chunks=resolved_chunks,
            )
        except _ABORTING_ERRORS as exc:
            raise ScoringError(f"provider unavailable: {exc}") from exc
        except Exception as exc:  # a measured outcome, not an operational failure
            return CaseResult.errored(
                loaded.name, loaded.dimensions, str(exc), latency_ms=_elapsed_ms(start)
            )
        latency_ms = _elapsed_ms(start)

        deterministic = score_case(
            narrative=generated.narrative,
            raw_indexes=generated.cited_chunk_indexes,
            context=case.context,
            grading=case.grading,
        )
        try:
            verdicts = await judge_client.score_rubric(
                narrative=generated.narrative,
                summary=case.summary,
                evidence=dict(case.evidence),
                chunks=resolved_chunks,
                rubric=case.grading.rubric,
            )
        except _ABORTING_ERRORS as exc:
            raise ScoringError(f"judge provider unavailable: {exc}") from exc
        except Exception as exc:  # a measured outcome, not an operational failure
            return CaseResult.errored(
                loaded.name,
                loaded.dimensions,
                f"judge call failed: {exc}",
                latency_ms=latency_ms,
            )

    judge = to_judge_score(case.grading.rubric, verdicts)
    return CaseResult(
        name=loaded.name,
        dimensions=loaded.dimensions,
        error=None,
        narrative=generated.narrative,
        raw_indexes=tuple(generated.cited_chunk_indexes),
        cited_ids=deterministic.cited_ids,
        out_of_range=deterministic.out_of_range,
        citation=deterministic.citation,
        check=deterministic.check,
        judge=judge,
        deterministic_pass=deterministic.passed,
        full_pass=deterministic.passed and judge.gate,
        latency_ms=latency_ms,
    )


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def format_summary(report: RunReport, run_path: Path) -> str:
    """A per-case table plus the run aggregates, for stdout."""
    totals = report.totals
    lines = [
        f"scored {totals.cases} case(s) via "
        f"{report.config.provider}/{report.config.model}",
    ]
    for case in report.cases:
        if case.is_errored:
            lines.append(f"  {case.name:<44} ERROR  {case.error}")
            continue
        det = "pass" if case.deterministic_pass else "FAIL"
        full = "pass" if case.full_pass else "FAIL"
        citation = case.citation
        detail = (
            f"recall={citation.recall:.2f} spurious={citation.spurious}"
            if citation is not None
            else ""
        )
        oor = f" out-of-range={list(case.out_of_range)}" if case.out_of_range else ""
        lines.append(f"  {case.name:<44} det={det:<4} full={full:<4} {detail}{oor}")
    lines += [
        f"  {'':<44} ----",
        f"  deterministic pass : {totals.deterministic_pass}/{totals.cases} "
        f"({totals.deterministic_pass_rate})",
        f"  full pass          : {totals.full_pass}/{totals.cases} "
        f"({totals.full_pass_rate})",
        f"  errored            : {totals.errored}/{totals.cases} ({totals.error_rate})",
        f"  mean recall        : {totals.mean_recall}",
        f"  mean precision     : {totals.mean_precision}",
        f"  spurious rate      : {totals.spurious_rate}",
        f"  out-of-range rate  : {totals.out_of_range_rate}",
    ]
    for check_id, tally in totals.per_check.items():
        lines.append(
            f"  check  - {check_id:<35}: {tally.passed}/{tally.total} ({tally.rate})"
        )
    for statement_id, tally in totals.per_must.items():
        lines.append(
            f"  must   - {statement_id:<35}: {tally.passed}/{tally.total} ({tally.rate})"
        )
    for statement_id, tally in totals.per_should.items():
        lines.append(
            f"  should - {statement_id:<35}: {tally.passed}/{tally.total} ({tally.rate})"
        )
    lines.append(f"run file: {run_path}")
    return "\n".join(lines)
