"""Specify invariants over the committed explanation cases."""

import json
from pathlib import Path

import pytest

from eval.explanation.build.casefile import CaseFile, iter_case_dirs, load_case_dir
from eval.explanation.build.chunking import IdentifiedChunk
from eval.explanation.build.prompts import render_case_prompt
from eval.explanation.paths import CHUNKS_JSON, PROMPT_TXT

pytestmark = pytest.mark.unit


def _handbook_chunks() -> list[IdentifiedChunk]:
    payload = json.loads(CHUNKS_JSON.read_text())
    return [
        IdentifiedChunk(id=c["id"], label=c["label"], content=c["content"])
        for c in payload["chunks"]
    ]


_CHUNKS = _handbook_chunks()
_CHUNK_IDS = {c.id for c in _CHUNKS}
_CASE_DIRS = iter_case_dirs()
_CASE_IDS = [p.name for p in _CASE_DIRS]


def _load(case_dir: Path) -> CaseFile:
    return load_case_dir(case_dir, _CHUNKS)


@pytest.mark.parametrize("case_dir", _CASE_DIRS, ids=_CASE_IDS)
def should_load_every_committed_case_clean(case_dir: Path) -> None:
    _load(case_dir)  # raises on any build-abort condition


@pytest.mark.parametrize("case_dir", _CASE_DIRS, ids=_CASE_IDS)
def should_reference_only_ids_present_in_chunks_json(case_dir: Path) -> None:
    case = _load(case_dir)
    assert set(case.context) <= _CHUNK_IDS
    assert set(case.grading.citations.ideal) <= _CHUNK_IDS


@pytest.mark.parametrize("case_dir", _CASE_DIRS, ids=_CASE_IDS)
def should_have_a_prompt_txt_matching_a_fresh_render(case_dir: Path) -> None:
    committed = (case_dir / PROMPT_TXT).read_text()
    assert committed == render_case_prompt(_load(case_dir), _CHUNKS)
