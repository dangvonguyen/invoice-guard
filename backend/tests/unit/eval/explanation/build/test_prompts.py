"""Specify per-case prompt rendering."""

import pytest

from eval.explanation.build.chunking import IdentifiedChunk
from eval.explanation.build.prompts import placeholder_chunk_id, resolve_context

pytestmark = pytest.mark.unit

_CONTEXT = ("2. Lodging#0", "6. Timelines#0", "3. Meals#0")


def _fake_chunks(*ids: str) -> list[IdentifiedChunk]:
    return [
        IdentifiedChunk(id=cid, label=cid.split("#")[0], content=f"body of {cid}")
        for cid in ids
    ]


def should_resolve_context_ids_to_chunks_in_list_order() -> None:
    resolved = resolve_context(
        ["6. Timelines#0", "2. Lodging#0"], _fake_chunks(*_CONTEXT)
    )

    assert [c.section_label for c in resolved] == ["6. Timelines", "2. Lodging"]
    assert [c.content for c in resolved] == [
        "body of 6. Timelines#0",
        "body of 2. Lodging#0",
    ]


def should_use_a_deterministic_placeholder_chunk_id() -> None:
    assert placeholder_chunk_id("6. Timelines#0") == placeholder_chunk_id(
        "6. Timelines#0"
    )
    assert placeholder_chunk_id("6. Timelines#0") != placeholder_chunk_id(
        "2. Lodging#0"
    )
