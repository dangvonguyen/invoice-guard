"""Low-level formatting helpers for the on-disk scoring artifacts."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def rfc3339(timestamp: datetime) -> str:
    """Render ``timestamp`` as a ``YYYY-MM-DDTHH:MM:SSZ`` string."""
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def dump_json(obj: Any) -> str:
    """Pretty-print ``obj`` as JSON with a trailing newline."""
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append exactly one compact JSON line, creating the file if absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
