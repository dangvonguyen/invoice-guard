"""CLI: ``python -m eval.explanation.score`` (``poe eval:explain:score``)."""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from app.core.config import MODEL_PROVIDERS, get_settings
from eval._common.score.constants import DEFAULT_CONCURRENCY
from eval.explanation.score import harness
from eval.explanation.score.results import RunConfig


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
        prog="python -m eval.explanation.score",
        description="Score the explanation golden set against production generation.",
    )
    parser.add_argument("names", nargs="*", help="case-directory names to score")
    parser.add_argument(
        "--provider",
        choices=MODEL_PROVIDERS,
        help="override GENERATION_PROVIDER",
    )
    parser.add_argument(
        "--model",
        help="override GENERATION_MODEL",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="override GENERATION_MAX_TOKENS",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        help=f"parallel cases (default {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--judge-provider",
        choices=MODEL_PROVIDERS,
        help="override JUDGE_PROVIDER (defaults to the generation provider)",
    )
    parser.add_argument(
        "--judge-model",
        help="override JUDGE_MODEL (defaults to the generation model)",
    )
    parser.add_argument(
        "--judge-max-tokens",
        type=int,
        help="override JUDGE_MAX_TOKENS (defaults to the generation max-tokens)",
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
    provider = args.provider or settings.GENERATION_PROVIDER
    model = args.model or settings.GENERATION_MODEL
    max_tokens = args.max_tokens or settings.GENERATION_MAX_TOKENS
    return RunConfig(
        provider=provider,
        model=model,
        max_tokens=max_tokens,
        concurrency=args.concurrency or DEFAULT_CONCURRENCY,
        judge_provider=args.judge_provider or settings.JUDGE_PROVIDER or provider,
        judge_model=args.judge_model or settings.JUDGE_MODEL or model,
        judge_max_tokens=(
            args.judge_max_tokens or settings.JUDGE_MAX_TOKENS or max_tokens
        ),
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
