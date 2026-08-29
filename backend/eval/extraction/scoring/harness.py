"""Orchestrate a scoring run: load cases, drive the production pipeline, write
the run file and (for a whole-set run) the history line.
"""

import argparse
import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml
from anthropic import APIConnectionError as _AnthropicConnError
from anthropic import AuthenticationError as _AnthropicAuthError
from openai import APIConnectionError as _OpenAIConnError
from openai import AuthenticationError as _OpenAIAuthError

from app.core.config import MODEL_PROVIDERS, get_settings
from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.model import ExtractedInvoice, build_model_client
from app.services.extraction.pipeline import ExtractionPipeline
from eval import paths
from eval.extraction.scoring import gitmeta
from eval.extraction.scoring.aggregate import aggregate
from eval.extraction.scoring.artifacts import append_history_line, write_run_file
from eval.extraction.scoring.compare import compare_case
from eval.extraction.scoring.constants import DEFAULT_CONCURRENCY
from eval.extraction.scoring.models import CaseScore, RunConfig, RunReport

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
    document_text: str
    expected: ExtractedInvoice


async def main(argv: Sequence[str]) -> int:
    """Score the selected cases and write artifacts. Returns the process exit code."""
    args = _parse_args(argv)
    config = _resolve_config(args)

    git_commit = gitmeta.head_commit()
    git_dirty = gitmeta.is_dirty()

    cases = _select_cases(paths.CASES_DIR, args.names, args.dimensions)
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

    selector = _selector(args)
    report = RunReport(
        config=config,
        timestamp=datetime.now(UTC),
        git_commit=git_commit,
        git_dirty=git_dirty,
        selector=selector,
        cases=scores,
        totals=aggregate(scores),
    )
    run_path = write_run_file(report, paths.RUNS_DIR)
    if selector is None:
        append_history_line(report, paths.HISTORY_PATH, run_file=run_path.name)

    print(_summary(report, run_path))
    return 0


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m eval.extraction.scoring",
        description="Score the extraction golden set against the production pipeline.",
    )
    parser.add_argument("names", nargs="*", help="case-directory names to score")
    parser.add_argument(
        "--provider",
        choices=MODEL_PROVIDERS,
        help="override EXTRACTION_PROVIDER",
    )
    parser.add_argument(
        "--model",
        help="override EXTRACTION_MODEL",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="override EXTRACTION_MAX_TOKENS",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        help=f"parallel cases (default {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--dimension",
        action="append",
        default=[],
        dest="dimensions",
        metavar="TAG",
        help="score only cases carrying this dimension tag (repeatable)",
    )
    args = parser.parse_args(list(argv))
    if args.names and args.dimensions:
        parser.error("positional case names and --dimension are mutually exclusive")
    return args


def _resolve_config(args: argparse.Namespace) -> RunConfig:
    settings = get_settings()
    return RunConfig(
        provider=args.provider or settings.EXTRACTION_PROVIDER,
        model=args.model or settings.EXTRACTION_MODEL,
        max_tokens=args.max_tokens or settings.EXTRACTION_MAX_TOKENS,
        concurrency=args.concurrency or DEFAULT_CONCURRENCY,
    )


def _selector(args: argparse.Namespace) -> dict[str, list[str]] | None:
    if args.names:
        return {"names": list(args.names)}
    if args.dimensions:
        return {"dimensions": list(args.dimensions)}
    return None


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
        except _ABORTING_ERRORS as exc:
            raise ScoringError(f"provider unavailable: {exc}") from exc
        except Exception as exc:  # a measured outcome, not an operational failure
            return CaseScore.errored(
                case.name,
                case.dimensions,
                str(exc),
                latency_ms=_elapsed_ms(start),
                expected_line_count=len(case.expected.line_items),
            )
    return compare_case(
        case.expected,
        result.fields,
        name=case.name,
        dimensions=case.dimensions,
        confidence=result.confidence,
        confidence_reason=result.confidence_reason,
        latency_ms=_elapsed_ms(start),
    )


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _summary(report: RunReport, run_path: Path) -> str:
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
