"""Filesystem layout of the eval area, resolved from this file's location."""

from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent

GENERATION_DIR = EVAL_DIR / "extraction" / "generation"
ASSETS_DIR = GENERATION_DIR / "templates" / "assets"

GOLDEN_SET_DIR = EVAL_DIR / "golden_set" / "extraction"
CASES_DIR = GOLDEN_SET_DIR / "cases"
SCHEMA_PATH = GOLDEN_SET_DIR / "schema" / "expected_invoice.schema.json"
FORMATS_PATH = GOLDEN_SET_DIR / "formats.md"

REPORTS_DIR = EVAL_DIR / "reports"
EXTRACTION_REPORTS_DIR = REPORTS_DIR / "extraction"
RUNS_DIR = EXTRACTION_REPORTS_DIR / "runs"
HISTORY_PATH = EXTRACTION_REPORTS_DIR / "history.jsonl"

REPO_ROOT = EVAL_DIR.parent.parent

CASE_YAML = "case.yaml"
EXPECTED_JSON = "expected.json"
SOURCE_JSON = "source.json"
SOURCE_PDF = "source.pdf"
SOURCE_EXTRACTED_TXT = "source.extracted.txt"
