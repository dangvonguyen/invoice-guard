"""Root anchors for the eval tree. Task-specific paths live in ``<task>/paths.py``."""

from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
