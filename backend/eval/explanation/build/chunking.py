"""Wrap the app ``SectionChunker`` and derive a stable ID per chunk."""

from dataclasses import dataclass

from app.services.policies.chunking import Chunk, SectionChunker
from eval.explanation.build.constants import CHUNKER

PREAMBLE_LABEL = "_preamble"


@dataclass(frozen=True)
class IdentifiedChunk:
    """One chunk plus its derived, collision-checked ID."""

    id: str
    label: str
    content: str


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
