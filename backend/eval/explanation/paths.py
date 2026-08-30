"""Filesystem paths for the explanation eval, anchored at the eval root."""

from eval._layout import EVAL_DIR

# Build package inputs/outputs
BUILD_DIR = EVAL_DIR / "explanation" / "build"

# Golden set
GOLDEN_SET_DIR = EVAL_DIR / "golden_set" / "explanation"
CASES_DIR = GOLDEN_SET_DIR / "cases"

# Handbook
HANDBOOK_PDF = (
    EVAL_DIR
    / "golden_set"
    / "handbook"
    / "ABHES-Travel-Reimbursement-Policy_Updated-January-2024.pdf"
)
HANDBOOK_DIR = GOLDEN_SET_DIR / "handbook"
HANDBOOK_MD = HANDBOOK_DIR / "handbook.md"
CHUNKS_JSON = HANDBOOK_DIR / "chunks.json"
HANDBOOK_SOURCE_MD = HANDBOOK_DIR / "SOURCE.md"

# Static prompt / schema fixtures
PROMPT_DIR = GOLDEN_SET_DIR / "prompt"
INSTRUCTIONS_PATH = PROMPT_DIR / "instructions.txt"
JUDGE_INSTRUCTIONS_PATH = PROMPT_DIR / "judge_instructions.txt"
SCHEMA_DIR = GOLDEN_SET_DIR / "schema"
GENERATED_SCHEMA_PATH = SCHEMA_DIR / "generated_explanation.schema.json"
JUDGE_SCHEMA_PATH = SCHEMA_DIR / "judge_output.schema.json"

# Reports
REPORTS_DIR = EVAL_DIR / "reports" / "explanation"
RUNS_DIR = REPORTS_DIR / "runs"
HISTORY_PATH = REPORTS_DIR / "history.jsonl"

# Per-case fixture filenames
CASE_YAML = "case.yaml"
PROMPT_TXT = "prompt.txt"
