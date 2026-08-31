"""Specify invariants over the committed corpus and per-set artifacts."""

import json
import shutil
from pathlib import Path

import jsonschema
import pytest
import yaml

from app.services.extraction.model import ExtractedInvoice
from eval.extraction.build import render
from eval.extraction.build.templates import TEMPLATES, get_template
from eval.extraction.build.vocab import LABEL_SLOTS
from eval.extraction.paths import (
    CASES_DIR,
    FORMATS_PATH,
    SCHEMA_PATH,
)

pytestmark = pytest.mark.unit

_CASE_DIRS = sorted(p for p in CASES_DIR.iterdir() if p.is_dir())
_CASE_IDS = [p.name for p in _CASE_DIRS]


@pytest.mark.parametrize("case_dir", _CASE_DIRS, ids=_CASE_IDS)
def should_regenerate_each_case_byte_for_byte(case_dir: Path, tmp_path: Path) -> None:
    work = tmp_path / case_dir.name
    shutil.copytree(case_dir, work)
    committed = {
        name: (case_dir / name).read_bytes()
        for name in ("source.pdf", "source.extracted.txt", "expected.json")
    }

    render.generate_case(work)

    for name, original in committed.items():
        assert (work / name).read_bytes() == original, f"{case_dir.name}/{name} drifted"


@pytest.mark.parametrize("case_dir", _CASE_DIRS, ids=_CASE_IDS)
def should_validate_committed_expected_against_the_schema(case_dir: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    instance = json.loads((case_dir / "expected.json").read_text())

    jsonschema.validate(instance=instance, schema=schema)


@pytest.mark.parametrize("case_dir", _CASE_DIRS, ids=_CASE_IDS)
def should_name_a_real_template_and_known_label_slots(case_dir: Path) -> None:
    case = yaml.safe_load((case_dir / "case.yaml").read_text())

    get_template(case["template"])
    assert set(case.get("label_overrides") or {}) <= LABEL_SLOTS


def should_keep_the_expected_fields_schema_current() -> None:
    committed = json.loads(SCHEMA_PATH.read_text())

    assert committed == ExtractedInvoice.model_json_schema()


def should_keep_formats_md_current() -> None:
    assert FORMATS_PATH.read_text() == render.render_formats_md(TEMPLATES)
