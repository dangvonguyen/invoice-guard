"""Unit tests for verifying generated citations against retrieved chunks."""

from uuid import uuid4

import pytest

from app.database.models.policy_document import PolicyDocChunk
from app.schemas.explanation import CitationView
from app.services.explanations.service import _verify_citations

pytestmark = pytest.mark.unit

FIRST_CHUNK = PolicyDocChunk(
    id=uuid4(),
    policy_document_id=uuid4(),
    chunk_index=0,
    section_label="5.3 Allowed Currencies",
    content="Expenses must be submitted in USD, EUR, or GBP.",
    embedding=[0.1] * 1536,
)
SECOND_CHUNK = PolicyDocChunk(
    id=uuid4(),
    policy_document_id=uuid4(),
    chunk_index=1,
    section_label="5.4 Submission Windows",
    content="Expenses must be submitted within 90 days.",
    embedding=[0.2] * 1536,
)


def should_keep_only_citations_naming_a_retrieved_chunk() -> None:
    citations = _verify_citations([FIRST_CHUNK, SECOND_CHUNK], [1])

    assert citations == [
        CitationView(
            chunk_id=SECOND_CHUNK.id,
            section_label=SECOND_CHUNK.section_label,
            content=SECOND_CHUNK.content,
        )
    ]


def should_drop_a_cited_index_outside_the_retrieved_chunks() -> None:
    citations = _verify_citations([FIRST_CHUNK], [0, 1, -1])

    assert citations == [
        CitationView(
            chunk_id=FIRST_CHUNK.id,
            section_label=FIRST_CHUNK.section_label,
            content=FIRST_CHUNK.content,
        )
    ]
