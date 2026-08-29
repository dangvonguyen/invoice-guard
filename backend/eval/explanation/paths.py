"""Filesystem paths for the explanation eval, anchored at the eval root."""

from eval._layout import EVAL_DIR

# Build package inputs/outputs
BUILD_DIR = EVAL_DIR / "explanation" / "build"

# Golden set
GOLDEN_SET_DIR = EVAL_DIR / "golden_set" / "explanation"
CASES_DIR = GOLDEN_SET_DIR / "cases"

# Reports
REPORTS_DIR = EVAL_DIR / "reports" / "explanation"
RUNS_DIR = REPORTS_DIR / "runs"
HISTORY_PATH = REPORTS_DIR / "history.jsonl"

# Per-case fixture filenames
CASE_YAML = "case.yaml"
