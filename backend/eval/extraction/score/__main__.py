"""CLI: ``python -m eval.extraction.score``."""

import asyncio
import sys

from eval.extraction.score.harness import main

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
