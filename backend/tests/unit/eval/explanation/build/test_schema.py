"""Specify that the rendered prompt/schema fixtures match their source modules."""

import json

import pytest

from app.services.explanations.generation import GENERATION_INSTRUCTIONS, OUTPUT_SCHEMA
from eval.explanation.build import schema
from eval.explanation.score.judge import JUDGE_INSTRUCTIONS

pytestmark = pytest.mark.unit


def should_render_generation_fixtures_from_the_production_module() -> None:
    assert schema.render_instructions() == GENERATION_INSTRUCTIONS + "\n"
    assert json.loads(schema.render_output_schema()) == OUTPUT_SCHEMA


def should_render_judge_instructions_with_one_trailing_newline() -> None:
    rendered = schema.render_judge_instructions()

    assert rendered == JUDGE_INSTRUCTIONS + "\n"
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")
