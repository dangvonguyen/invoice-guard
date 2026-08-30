"""Collision-free naming and writing of the per-run JSON dump."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from eval._common.score.serialization import dump_json

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def write_run_json(
    directory: Path,
    payload: dict[str, Any],
    timestamp: datetime,
    provider: str,
    model: str,
) -> Path:
    """Write ``payload`` to a fresh run file under ``directory`` and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / run_filename(timestamp, provider, model, directory)
    path.write_text(dump_json(payload))
    return path


def run_filename(
    timestamp: datetime, provider: str, model: str, existing_dir: Path
) -> str:
    """Return a collision-free ``<basic-iso>_<provider>_<model>.json`` name."""
    stem = f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{provider}_{_UNSAFE_CHARS.sub('-', model)}"
    candidate = f"{stem}.json"
    suffix = 2
    while (existing_dir / candidate).exists():
        candidate = f"{stem}-{suffix}.json"
        suffix += 1
    return candidate
