"""Specify chunk-ID derivation over ``SectionChunker`` output."""

import pytest

from app.services.policies.chunking import Chunk
from eval.explanation.build.chunking import IdentifiedChunk, identify_chunks

pytestmark = pytest.mark.unit


def should_number_consecutive_same_label_chunks_from_zero() -> None:
    chunks = [
        Chunk(label="3 Air Travel", content="first"),
        Chunk(label="3 Air Travel", content="second"),
        Chunk(label="3 Air Travel", content="third"),
    ]

    assert [c.id for c in identify_chunks(chunks)] == [
        "3 Air Travel#0",
        "3 Air Travel#1",
        "3 Air Travel#2",
    ]


def should_reset_the_ordinal_when_the_label_changes() -> None:
    chunks = [
        Chunk(label="2 Lodging", content="a"),
        Chunk(label="3 Air Travel", content="b"),
        Chunk(label="3 Air Travel", content="c"),
    ]

    assert [c.id for c in identify_chunks(chunks)] == [
        "2 Lodging#0",
        "3 Air Travel#0",
        "3 Air Travel#1",
    ]


def should_fall_back_to_the_preamble_sentinel_for_a_none_label() -> None:
    [chunk] = identify_chunks([Chunk(label=None, content="intro text")])

    assert chunk == IdentifiedChunk(
        id="_preamble#0", label="_preamble", content="intro text"
    )


def should_abort_when_a_non_consecutive_label_repeat_collides() -> None:
    chunks = [
        Chunk(label="3 Air Travel", content="a"),
        Chunk(label="2 Lodging", content="b"),
        Chunk(label="3 Air Travel", content="c"),
    ]

    with pytest.raises(ValueError, match="collision"):
        identify_chunks(chunks)


def should_preserve_label_and_content_on_every_identified_chunk() -> None:
    chunks = [
        Chunk(label=None, content="preamble"),
        Chunk(label="1 Purpose", content="purpose body"),
        Chunk(label="2 Lodging", content="lodging body"),
    ]

    assert identify_chunks(chunks) == [
        IdentifiedChunk(id="_preamble#0", label="_preamble", content="preamble"),
        IdentifiedChunk(id="1 Purpose#0", label="1 Purpose", content="purpose body"),
        IdentifiedChunk(id="2 Lodging#0", label="2 Lodging", content="lodging body"),
    ]
