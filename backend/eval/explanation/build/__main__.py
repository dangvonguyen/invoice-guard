"""CLI: ``python -m eval.explanation.build``.

Takes no arguments. Regenerates the handbook extraction, its chunks, and the
static prompt/schema fixtures -- offline, keyless, diff-gated in CI.
"""

from eval.explanation.build import orchestrate


def main() -> int:
    orchestrate.build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
