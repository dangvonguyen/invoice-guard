"""Split a policy handbook's raw text into labeled, embeddable chunks."""

import re
from dataclasses import dataclass
from typing import Protocol

_MAX_HEADING_LENGTH = 70

# Match short, title-cased numbered headings, not numbered sentences.
_HEADING_PATTERN = re.compile(
    rf"^\d+(?:\.\d+)*(?:\.)?[ \t]+[A-Z][^.\n]{{0,{_MAX_HEADING_LENGTH - 1}}}$",
    re.MULTILINE,
)


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


@dataclass(frozen=True)
class Section:
    """One labeled span of a policy document's text."""

    label: str | None
    text: str


def split_into_sections(document_text: str) -> list[Section]:
    """Split text into one section per numbered heading (e.g. "5.2 Title").

    A document with no detected heading is returned as a single section
    with `label=None`.
    """
    headings = list(_HEADING_PATTERN.finditer(document_text))
    if not headings:
        return [Section(label=None, text=document_text)]

    sections = []
    prefix = document_text[: headings[0].start()].strip()
    if prefix:
        sections.append(Section(label=None, text=prefix))

    for heading, next_heading in zip(headings, [*headings[1:], None], strict=True):
        end = next_heading.start() if next_heading else len(document_text)
        sections.append(
            Section(
                label=heading.group().strip(),
                text=document_text[heading.end() : end].strip(),
            )
        )
    return sections


def count_words(text: str) -> int:
    """Approximate a chunk's token count by its word count."""
    return len(text.split())


class SectionChunker:
    """Split a document's sections into token-budgeted, embeddable chunks."""

    def __init__(self, *, min_tokens: int, max_tokens: int) -> None:
        self._min_tokens = min_tokens
        self._max_tokens = max_tokens

    def chunk(self, document_text: str) -> list[Chunk]:
        """Return the document's sections split into labeled, budgeted chunks."""
        return [
            Chunk(label=section.label, content=chunk_text)
            for section in split_into_sections(document_text)
            for chunk_text in self._chunk_section(section.text)
        ]

    def _chunk_section(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current = paragraphs[0]
        for paragraph in paragraphs[1:]:
            candidate = f"{current}\n\n{paragraph}"
            if (
                count_words(current) >= self._min_tokens
                and count_words(candidate) > self._max_tokens
            ):
                chunks.append(current)
                current = paragraph
            else:
                current = candidate

        if chunks and count_words(current) < self._min_tokens:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
        else:
            chunks.append(current)
        return chunks
