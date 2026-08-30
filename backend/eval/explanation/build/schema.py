"""Render the static prompt/schema fixtures."""

import json

from app.services.explanations.generation import GENERATION_INSTRUCTIONS, OUTPUT_SCHEMA
from eval.explanation.score.judge import JUDGE_INSTRUCTIONS, JUDGE_OUTPUT_SCHEMA


def render_instructions() -> str:
    """The generation instruction string, one trailing newline."""
    return GENERATION_INSTRUCTIONS + "\n"


def render_output_schema() -> str:
    """The generation output schema as pretty JSON, one trailing newline."""
    return json.dumps(OUTPUT_SCHEMA, indent=2, ensure_ascii=False) + "\n"


def render_judge_instructions() -> str:
    """The judge instruction string, one trailing newline."""
    return JUDGE_INSTRUCTIONS + "\n"


def render_judge_output_schema() -> str:
    """The judge output schema as pretty JSON, one trailing newline."""
    return json.dumps(JUDGE_OUTPUT_SCHEMA, indent=2, ensure_ascii=False) + "\n"
