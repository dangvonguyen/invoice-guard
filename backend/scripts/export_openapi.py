"""Export the FastAPI OpenAPI schema to the file the frontend generates types from."""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings
from app.core.helpers import get_project_root
from app.main import app

DEFAULT_OUTPUT = get_project_root().parent / "frontend" / "api" / "openapi.yml"


class IndentedDumper(yaml.SafeDumper):
    """Indent block sequence items under their key."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        super().increase_indent(flow, indentless=False)


def build_schema() -> dict[str, Any]:
    """Return the OpenAPI schema as the app serves it under its root path."""
    schema: dict[str, Any] = app.openapi()
    # FastAPI adds the root-path server only when answering a live request,
    # so the in-process schema needs it appended.
    schema["servers"] = [{"url": get_settings().API_ROOT}]
    return schema


def render_openapi() -> str:
    """Return the schema as YAML text in the frontend's on-disk format."""
    return yaml.dump(
        build_schema(),
        Dumper=IndentedDumper,
        sort_keys=False,
        allow_unicode=True,
    )


def export_openapi(output: Path) -> bool:
    """Write the schema to ``output``; return ``True`` if its content changed."""
    rendered = render_openapi()
    if output.exists() and output.read_text() == rendered:
        return False
    output.write_text(rendered)
    return True


def is_in_sync(output: Path) -> bool:
    """Return whether ``output`` already matches the app's schema."""
    return output.exists() and output.read_text() == render_openapi()


def main() -> None:
    """Export or verify the OpenAPI schema from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to write the schema to (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the file is stale instead of writing it",
    )
    args = parser.parse_args()

    if args.check:
        if is_in_sync(args.output):
            print(f"{args.output} is up to date.")
            return
        print(
            f"{args.output} is out of sync; run `poe openapi:export`.", file=sys.stderr
        )
        raise SystemExit(1)

    changed = export_openapi(args.output)
    print(f"{'Wrote' if changed else 'No change to'} {args.output}.")


if __name__ == "__main__":
    main()
