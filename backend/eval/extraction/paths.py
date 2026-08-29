"""Filesystem paths for the extraction eval, anchored at the eval root."""

from eval._layout import EVAL_DIR

# Build package inputs/outputs
BUILD_DIR = EVAL_DIR / "extraction" / "build"
FONTS_DIR = BUILD_DIR / "templates" / "assets"

# Golden set
GOLDEN_SET_DIR = EVAL_DIR / "golden_set" / "extraction"
CASES_DIR = GOLDEN_SET_DIR / "cases"
SCHEMA_PATH = GOLDEN_SET_DIR / "schema" / "expected_invoice.schema.json"
FORMATS_PATH = GOLDEN_SET_DIR / "formats.md"

# Reports
REPORTS_DIR = EVAL_DIR / "reports" / "extraction"
RUNS_DIR = REPORTS_DIR / "runs"
HISTORY_PATH = REPORTS_DIR / "history.jsonl"

# Per-case fixture filenames
CASE_YAML = "case.yaml"
EXPECTED_JSON = "expected.json"
SOURCE_JSON = "source.json"
SOURCE_PDF = "source.pdf"
SOURCE_EXTRACTED_TXT = "source.extracted.txt"
