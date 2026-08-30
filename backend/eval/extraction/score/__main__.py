"""CLI: ``python -m eval.extraction.score`` (``poe eval:extract:score``)."""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.core.config import MODEL_PROVIDERS, get_settings
from eval._common.score.constants import DEFAULT_CONCURRENCY
from eval.extraction.score import harness
from eval.extraction.score.results import RunConfig


async def main(argv: Sequence[str]) -> int:
    """Score the selected cases and write artifacts. Returns the process exit code."""
    args = _parse_args(argv)
    config = _resolve_config(args)
    report, run_path = await harness.run(
        config=config,
        names=args.names,
        dimensions=args.dimensions,
    )
    print(harness.format_summary(report, run_path))
    return 0


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m eval.extraction.score",
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


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
