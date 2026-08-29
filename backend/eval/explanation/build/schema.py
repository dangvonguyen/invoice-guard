"""Render the static prompt/schema fixtures from the production generation module."""

import json

from app.services.explanations.generation import GENERATION_INSTRUCTIONS, OUTPUT_SCHEMA


def render_instructions() -> str:
    """The generation instruction string, one trailing newline."""
    return GENERATION_INSTRUCTIONS + "\n"


def render_output_schema() -> str:
    """The generation output schema as pretty JSON, one trailing newline."""
    return json.dumps(OUTPUT_SCHEMA, indent=2, ensure_ascii=False) + "\n"
