"""CLI: ``python -m eval.extraction.generation [<case_id> | --emit-schema]``.

No arguments regenerates every case plus the schema and formats registry; a
positional case-directory name regenerates one case; ``--emit-schema`` only
rewrites the expected-fields JSON schema.
"""

import sys

from eval.extraction.generation import render
from eval.paths import CASES_DIR


def main(argv: list[str]) -> int:
    if "--emit-schema" in argv:
        render.emit_schema()
        return 0
    if argv:
        render.generate_case(CASES_DIR / argv[0])
        return 0
    render.generate_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
