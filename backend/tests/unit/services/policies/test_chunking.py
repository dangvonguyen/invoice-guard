"""Specify how a policy handbook's text is split into sections and chunks."""

import pytest

from app.services.policies.chunking import SectionChunker, split_into_sections

pytestmark = pytest.mark.unit


def handbook_text() -> str:
    """Build handbook text with two numbered sections."""
    return (
        "5.1 Meals\n"
        "Employees may expense meals up to $75 per day.\n\n"
        "5.2 Client Entertainment\n"
        "Client entertainment requires manager pre-approval.\n"
    )


def should_start_a_new_section_at_each_numbered_heading_line() -> None:
    """Split a document into one section per numbered heading."""
    sections = split_into_sections(handbook_text())

    assert [section.label for section in sections] == [
        "5.1 Meals",
        "5.2 Client Entertainment",
    ]
    assert "$75" in sections[0].text
    assert "pre-approval" in sections[1].text


def should_treat_a_document_with_zero_detected_headings_as_a_single_section() -> None:
    """Fall back to one implicit, unlabeled section when no heading matches."""
    text = "Just plain prose with no numbered headings at all."

    sections = split_into_sections(text)

    assert len(sections) == 1
    assert sections[0].label is None
    assert sections[0].text == text


def should_preserve_text_before_the_first_numbered_heading() -> None:
    """Return introductory policy text as an implicit, unlabeled section."""
    text = (
        "These rules apply to all employees.\n\n"
        "5.1 Meals\n"
        "Employees may expense meals up to $75 per day."
    )

    sections = split_into_sections(text)

    assert [section.label for section in sections] == [None, "5.1 Meals"]
    assert sections[0].text == "These rules apply to all employees."
    assert "$75" in sections[1].text


def should_produce_one_chunk_per_section_when_every_section_fits_the_budget() -> None:
    """Turn each detected section into its own labeled, embeddable chunk."""
    chunker = SectionChunker(min_tokens=1, max_tokens=100)

    chunks = chunker.chunk(handbook_text())

    assert [chunk.label for chunk in chunks] == [
        "5.1 Meals",
        "5.2 Client Entertainment",
    ]
    assert "5.1 Meals" not in chunks[0].content
    assert "$75" in chunks[0].content
