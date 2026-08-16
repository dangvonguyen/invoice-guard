"""Split a policy handbook's raw text into labeled, embeddable chunks."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Chunk:
    """One labeled, embeddable slice of a policy document's text."""

    label: str | None
    content: str


class Chunker(Protocol):
    """Split a document's full text into labeled chunks ready to embed."""

    def chunk(self, document_text: str) -> list[Chunk]:
        """Return the document's text split into labeled chunks."""
        ...
