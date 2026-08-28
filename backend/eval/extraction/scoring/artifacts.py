"""Serialise a :class:`RunReport` to the two on-disk artifacts.

- ``runs/<timestamp>_<provider>_<model>.json`` — pretty, one per run, git-ignored.
- ``history.jsonl`` — one compact fixed-key-order line per whole-set run, committed.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from eval.extraction.scoring.constants import HISTORY_LINE_VERSION, RUN_SCHEMA_VERSION
from eval.extraction.scoring.models import CaseScore, CaseTally, RunReport

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


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


def write_run_file(report: RunReport, directory: Path) -> Path:
    """Write the ``schema_version: 1`` run file and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    name = run_filename(
        report.timestamp, report.config.provider, report.config.model, directory
    )
    path = directory / name
    path.write_text(_dump_json(_run_payload(report)))
    return path


def append_history_line(report: RunReport, path: Path, *, run_file: str) -> None:
    """Append exactly one compact history line, creating the file if absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_history_payload(report, run_file), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _run_payload(report: RunReport) -> dict[str, Any]:
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run": {
            "timestamp": _rfc3339(report.timestamp),
            "provider": report.config.provider,
            "model": report.config.model,
            "max_tokens": report.config.max_tokens,
            "concurrency": report.config.concurrency,
            "git_commit": report.git_commit,
            "git_dirty": report.git_dirty,
            "selector": report.selector,
            "case_count": len(report.cases),
        },
        "totals": {
            **_tally_payload(report.totals),
            "by_dimension": {
                tag: _tally_payload(tally)
                for tag, tally in report.totals.by_dimension.items()
            },
        },
        "cases": [_case_payload(case) for case in report.cases],
    }


def _tally_payload(tally: CaseTally) -> dict[str, Any]:
    return {
        "cases": tally.cases,
        "fully_correct": tally.fully_correct,
        "fully_correct_rate": tally.fully_correct_rate,
        "error_count": tally.error_count,
        "error_rate": tally.error_rate,
        "field_accuracy": {
            field: {"correct": ft.correct, "total": ft.total, "rate": ft.rate}
            for field, ft in tally.field_accuracy.items()
        },
    }


def _case_payload(case: CaseScore) -> dict[str, Any]:
    fields = (
        None
        if case.fields is None
        else {field: _pair(fc) for field, fc in case.fields.items()}
    )
    line_items = None
    if case.line_items is not None:
        line_items = {
            "ordered_match": case.line_items.ordered_match,
            "unordered_match": case.line_items.unordered_match,
            "expected_count": case.line_items.expected_count,
            "actual_count": case.line_items.actual_count,
            "rows": [
                {
                    "index": row.index,
                    **{sub: _pair(fc) for sub, fc in row.fields.items()},
                }
                for row in case.line_items.rows
            ],
        }
    return {
        "name": case.name,
        "dimensions": list(case.dimensions),
        "fully_correct": case.fully_correct,
        "error": case.error,
        "confidence": case.confidence,
        "confidence_reason": case.confidence_reason,
        "latency_ms": case.latency_ms,
        "fields": fields,
        "line_items": line_items,
    }


def _history_payload(report: RunReport, run_file: str) -> dict[str, Any]:
    return {
        "v": HISTORY_LINE_VERSION,
        "timestamp": _rfc3339(report.timestamp),
        "git_commit": report.git_commit,
        "git_dirty": report.git_dirty,
        "provider": report.config.provider,
        "model": report.config.model,
        "max_tokens": report.config.max_tokens,
        "cases": report.totals.cases,
        "fully_correct_rate": report.totals.fully_correct_rate,
        "error_rate": report.totals.error_rate,
        "field_accuracy": {
            field: ft.rate for field, ft in report.totals.field_accuracy.items()
        },
        "run_file": run_file,
    }


def _pair(fc: Any) -> dict[str, Any]:
    return {"expected": fc.expected, "actual": fc.actual, "match": fc.match}


def _rfc3339(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
