"""Specify SQL-backed policy document persistence and activation behavior."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.policy_document import (
    EMBEDDING_DIMENSIONS,
    PolicyDocChunk,
    PolicyDocument,
    PolicyDocumentStatus,
)
from app.database.repositories.policy_document import (
    NewPolicyChunk,
    PolicyDocumentRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


def embedding(seed: float) -> list[float]:
    """Build a fixed-length vector matching the configured embedding dimensions."""
    return [seed] * EMBEDDING_DIMENSIONS


def one_hot(*indexes: int) -> list[float]:
    """Build a vector with 1.0 at the given indexes, so distance is measurable."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for index in indexes:
        vector[index] = 1.0
    return vector


@pytest.fixture
def repository(test_db: AsyncSession) -> PolicyDocumentRepository:
    """Return a policy document repository using the test database session."""
    return PolicyDocumentRepository(session=test_db)


async def should_activate_the_first_upload_with_its_chunks(
    test_db: AsyncSession, repository: PolicyDocumentRepository
) -> None:
    """Persist a new document as active along with its embedded chunks."""
    document = await repository.activate(
        original_filename="expense-handbook-v1.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="5.1 Meals",
                content="Meals text",
                embedding=embedding(0.1),
            ),
            NewPolicyChunk(
                section_label="5.2 Entertainment",
                content="Entertainment text",
                embedding=embedding(0.2),
            ),
        ],
    )

    assert document.status == PolicyDocumentStatus.ACTIVE

    stored = await test_db.get(PolicyDocument, document.id)
    assert stored is not None
    assert stored.status == PolicyDocumentStatus.ACTIVE
    assert stored.original_filename == "expense-handbook-v1.pdf"

    chunks = (
        await test_db.scalars(
            select(PolicyDocChunk).where(
                PolicyDocChunk.policy_document_id == document.id
            )
        )
    ).all()
    assert len(chunks) == 2
    assert {chunk.section_label for chunk in chunks} == {
        "5.1 Meals",
        "5.2 Entertainment",
    }


async def should_supersede_the_previously_active_document(
    test_db: AsyncSession, repository: PolicyDocumentRepository
) -> None:
    """Activating a new document demotes the current active one, atomically."""
    first = await repository.activate(
        original_filename="expense-handbook-v1.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="5.1 Meals",
                content="Meals text",
                embedding=embedding(0.1),
            ),
        ],
    )

    second = await repository.activate(
        original_filename="expense-handbook-v2.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="5.1 Meals",
                content="Updated meals text",
                embedding=embedding(0.2),
            ),
        ],
    )

    assert second.status == PolicyDocumentStatus.ACTIVE

    stored_first = await test_db.get(PolicyDocument, first.id)
    assert stored_first is not None
    assert stored_first.status == PolicyDocumentStatus.SUPERSEDED

    active_documents = (
        await test_db.scalars(
            select(PolicyDocument).where(
                PolicyDocument.status == PolicyDocumentStatus.ACTIVE
            )
        )
    ).all()
    assert [document.id for document in active_documents] == [second.id]


async def should_list_the_activated_document_with_its_chunk_count(
    repository: PolicyDocumentRepository,
) -> None:
    """Return every document alongside how many chunks it has."""
    await repository.activate(
        original_filename="expense-handbook-v1.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="5.1 Meals",
                content="Meals text",
                embedding=embedding(0.1),
            ),
            NewPolicyChunk(
                section_label="5.2 Entertainment",
                content="Entertainment text",
                embedding=embedding(0.2),
            ),
        ],
    )

    documents = await repository.list_all()

    assert len(documents) == 1
    document, chunk_count = documents[0]
    assert document.status == PolicyDocumentStatus.ACTIVE
    assert chunk_count == 2


async def should_return_the_top_k_chunks_nearest_the_query_embedding(
    repository: PolicyDocumentRepository,
) -> None:
    """Order results by cosine distance and cut off at top_k."""
    await repository.activate(
        original_filename="expense-handbook-v1.pdf",
        chunks=[
            NewPolicyChunk(section_label="near", content="near", embedding=one_hot(0)),
            NewPolicyChunk(section_label="mid", content="mid", embedding=one_hot(0, 1)),
            NewPolicyChunk(section_label="far", content="far", embedding=one_hot(1)),
        ],
    )

    chunks = await repository.search_similar_chunks(embedding=one_hot(0), top_k=2)

    assert [chunk.section_label for chunk in chunks] == ["near", "mid"]


async def should_scope_similarity_search_to_the_active_documents_chunks(
    repository: PolicyDocumentRepository,
) -> None:
    """Never return a superseded document's chunk, however close it scores."""
    await repository.activate(
        original_filename="expense-handbook-v1.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="superseded", content="superseded", embedding=one_hot(0)
            ),
        ],
    )
    await repository.activate(
        original_filename="expense-handbook-v2.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="active", content="active", embedding=one_hot(1)
            ),
        ],
    )

    chunks = await repository.search_similar_chunks(embedding=one_hot(0), top_k=5)

    assert [chunk.section_label for chunk in chunks] == ["active"]
