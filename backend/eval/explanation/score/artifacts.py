"""Serialize a :class:`RunReport` to the on-disk artifacts.

- ``runs/<timestamp>_<provider>_<model>.json`` — pretty, one per run, git-ignored.
- ``history.jsonl`` — one compact fixed-key-order line per whole-set run, committed.
"""

import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from eval.explanation.score.constants import (
    HISTORY_LINE_VERSION,
    RUN_SCHEMA_VERSION,
)
from eval.explanation.score.results import (
    CaseResult,
    CheckScore,
    CitationScore,
    JudgeScore,
    RunReport,
    RunTally,
    Tally,
)

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
    """Write the full per-case run dump and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    name = run_filename(
        report.timestamp, report.config.provider, report.config.model, directory
    )
    path = directory / name
    path.write_text(_dump_json(_run_payload(report)))
    return path


def append_history_line(report: RunReport, path: Path, *, run_file: str) -> None:
    """Append exactly one compact history line, creating the file if absent."""
    _append_jsonl(path, _history_payload(report, run_file))


def append_history_if_whole_set(
    report: RunReport, path: Path, *, run_file: str
) -> bool:
    """Append a deterministic history line only for a whole-set run (no selector)."""
    if report.selector is not None:
        return False
    _append_jsonl(path, _history_payload(report, run_file))
    return True


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append exactly one compact JSON line, creating the file if absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
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


def _tally_payload(tally: RunTally) -> dict[str, Any]:
    return {
        "cases": tally.cases,
        "scored": tally.scored,
        "errored": tally.errored,
        "error_rate": tally.error_rate,
        "deterministic_pass": tally.deterministic_pass,
        "deterministic_pass_rate": tally.deterministic_pass_rate,
        "full_pass": tally.full_pass,
        "full_pass_rate": tally.full_pass_rate,
        "spurious_cases": tally.spurious_cases,
        "spurious_rate": tally.spurious_rate,
        "out_of_range_cases": tally.out_of_range_cases,
        "out_of_range_rate": tally.out_of_range_rate,
        "mean_precision": tally.mean_precision,
        "mean_recall": tally.mean_recall,
        "per_check": _tally_map_payload(tally.per_check),
        "per_must": _tally_map_payload(tally.per_must),
        "per_should": _tally_map_payload(tally.per_should),
    }


def _tally_map_payload(tallies: Mapping[str, Tally]) -> dict[str, Any]:
    return {
        key: {"passed": t.passed, "total": t.total, "rate": t.rate}
        for key, t in tallies.items()
    }


def _case_payload(case: CaseResult) -> dict[str, Any]:
    return {
        "name": case.name,
        "dimensions": list(case.dimensions),
        "error": case.error,
        "narrative": case.narrative,
        "raw_indexes": list(case.raw_indexes),
        "cited_ids": list(case.cited_ids),
        "out_of_range": list(case.out_of_range),
        "citation": _citation_payload(case.citation),
        "checks": _check_payload(case.check),
        "judge": _judge_payload(case.judge),
        "deterministic_pass": case.deterministic_pass,
        "full_pass": case.full_pass,
        "latency_ms": case.latency_ms,
    }


def _citation_payload(citation: CitationScore | None) -> dict[str, Any] | None:
    if citation is None:
        return None
    return {
        "recall": citation.recall,
        "precision": citation.precision,
        "spurious": citation.spurious,
        "gate": citation.gate,
    }


def _check_payload(check: CheckScore | None) -> dict[str, Any] | None:
    if check is None:
        return None
    return {
        "gate": check.gate,
        "results": [
            {
                "id": r.id,
                "kind": r.kind,
                "pattern": r.pattern,
                "passed": r.passed,
            }
            for r in check.results
        ],
    }


def _judge_payload(judge: JudgeScore | None) -> dict[str, Any] | None:
    if judge is None:
        return None
    return {
        "gate": judge.gate,
        "results": [
            {
                "id": r.id,
                "severity": r.severity,
                "passed": r.passed,
                "reason": r.reason,
            }
            for r in judge.results
        ],
    }


def _history_payload(report: RunReport, run_file: str) -> dict[str, Any]:
    totals = report.totals
    return {
        "v": HISTORY_LINE_VERSION,
        "timestamp": _rfc3339(report.timestamp),
        "git_commit": report.git_commit,
        "git_dirty": report.git_dirty,
        "gen_provider": report.config.provider,
        "gen_model": report.config.model,
        "judge_provider": report.config.judge_provider,
        "judge_model": report.config.judge_model,
        "cases": totals.cases,
        "errored": totals.errored,
        "deterministic_pass_rate": totals.deterministic_pass_rate,
        "full_pass_rate": totals.full_pass_rate,
        "mean_precision": totals.mean_precision,
        "mean_recall": totals.mean_recall,
        "spurious_rate": totals.spurious_rate,
        "out_of_range_rate": totals.out_of_range_rate,
        "per_check": {check_id: t.rate for check_id, t in totals.per_check.items()},
        "per_must": {sid: t.rate for sid, t in totals.per_must.items()},
        "per_should": {sid: t.rate for sid, t in totals.per_should.items()},
        "run_file": run_file,
    }


def _rfc3339(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
