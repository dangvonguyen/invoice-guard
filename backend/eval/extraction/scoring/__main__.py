"""CLI: ``python -m eval.extraction.scoring``."""

import asyncio
import sys

from eval.extraction.scoring.harness import main

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
