"""Wrap the app ``SectionChunker`` and derive a stable ID per chunk."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.services.policies.chunking import Chunk, SectionChunker
from eval.explanation.build.constants import CHUNKER

PREAMBLE_LABEL = "_preamble"


@dataclass(frozen=True)
class IdentifiedChunk:
    """One chunk plus its derived, collision-checked ID."""

    id: str
    label: str
    content: str

    def as_dict(self) -> dict[str, str]:
        """The ``chunks.json`` record for this chunk."""
        return {"id": self.id, "label": self.label, "content": self.content}

    @classmethod
    def from_dict(cls, record: dict[str, str]) -> "IdentifiedChunk":
        """Rebuild a chunk from its ``chunks.json`` record."""
        return cls(id=record["id"], label=record["label"], content=record["content"])


def identify_chunks(chunks: list[Chunk]) -> list[IdentifiedChunk]:
    """Attach ``"{label}#{ordinal}"`` IDs, aborting on a collision.

    Ordinals are assigned by grouping consecutive same-label chunks, so a label
    that reappears after a different label restarts at ``#0`` and collides with
    its earlier run -- a degenerate split that must fail the build, not ship.
    """
    identified: list[IdentifiedChunk] = []
    seen: set[str] = set()
    previous_label: str | None = None
    ordinal = 0

    for chunk in chunks:
        label = chunk.label if chunk.label is not None else PREAMBLE_LABEL
        ordinal = ordinal + 1 if label == previous_label else 0
        previous_label = label

        chunk_id = f"{label}#{ordinal}"
        if chunk_id in seen:
            raise ValueError(
                f"chunk ID collision: {chunk_id!r} is produced by two chunks; "
                f"a non-consecutive repeat of label {label!r} broke ordinal derivation"
            )
        seen.add(chunk_id)
        identified.append(
            IdentifiedChunk(id=chunk_id, label=label, content=chunk.content)
        )

    return identified


def chunk_handbook(text: str) -> list[IdentifiedChunk]:
    """Chunk the handbook text with the frozen params and derive IDs."""
    chunker = SectionChunker(
        min_tokens=CHUNKER["min_tokens"], max_tokens=CHUNKER["max_tokens"]
    )
    return identify_chunks(chunker.chunk(text))


def read_chunks(path: Path) -> list[IdentifiedChunk]:
    """Load a committed ``chunks.json`` back into :class:`IdentifiedChunk` objects."""
    payload = json.loads(path.read_text())
    return [IdentifiedChunk.from_dict(record) for record in payload["chunks"]]
