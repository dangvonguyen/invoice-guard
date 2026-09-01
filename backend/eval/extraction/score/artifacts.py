"""Serialise a :class:`RunReport` to the two on-disk artifacts.

- ``runs/<timestamp>_<provider>_<model>.json`` — pretty, one per run, git-ignored.
- ``history.jsonl`` — one compact fixed-key-order line per whole-set run, committed.
"""

from pathlib import Path
from typing import Any

from eval._common.score.run_files import write_run_json
from eval._common.score.serialization import append_jsonl, rfc3339
from eval.extraction.score.constants import HISTORY_LINE_VERSION, RUN_SCHEMA_VERSION
from eval.extraction.score.results import CaseScore, CaseTally, RunReport


def write_run_file(report: RunReport, dir: Path) -> Path:
    """Write the run file and return its path."""
    return write_run_json(
        dir,
        _run_payload(report),
        report.timestamp,
        report.config.provider,
        report.config.model,
    )


def append_history_line(report: RunReport, path: Path, *, run_file: str) -> None:
    """Append one compact history line, creating the file if absent."""
    append_jsonl(path, _history_payload(report, run_file))


def _run_payload(report: RunReport) -> dict[str, Any]:
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run": {
            "timestamp": rfc3339(report.timestamp),
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
        "timestamp": rfc3339(report.timestamp),
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
