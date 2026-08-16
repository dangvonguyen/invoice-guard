"""Specify how policy ingestion service coordinates chunking, embedding, and activation."""

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.database.models.policy_document import PolicyDocument, PolicyDocumentStatus
from app.database.repositories.policy_document import NewPolicyChunk
from app.services.policies.chunking import Chunk
from app.services.policies.ingestion import PolicyIngestionService

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

DOCUMENT_TEXT = "5.1 Meals\nEmployees may expense meals up to $75 per day."
SECTION_LABEL = "5.1 Meals"
CHUNK_CONTENT = "Employees may expense meals up to $75 per day."
FILENAME = "expense-handbook-v1.pdf"
CONTENT = b"%PDF-1.4 fake bytes"


@pytest.fixture
def text_extractor() -> Mock:
    """Stand in for the PDF text-layer boundary with a fixed document text."""
    extractor = Mock()
    extractor.extract_text.return_value = DOCUMENT_TEXT
    return extractor


@pytest.fixture
def chunker() -> Mock:
    """Stand in for the section/chunk-splitting boundary with one fixed chunk."""
    chunker = Mock()
    chunker.chunk.return_value = [Chunk(label=SECTION_LABEL, content=CHUNK_CONTENT)]
    return chunker


@pytest.fixture
def embedding_client() -> AsyncMock:
    """Stand in for the embedding-provider boundary with a fixed vector."""
    client = AsyncMock()
    client.embed_batch.return_value = [[0.1, 0.2, 0.3]]
    return client


@pytest.fixture
def policy_documents() -> AsyncMock:
    """Stand in for the persistence boundary, returning the activated document."""
    repository = AsyncMock()
    repository.activate.return_value = PolicyDocument(
        id=UUID("00000000-0000-0000-0000-0000000000aa"),
        original_filename=FILENAME,
        status=PolicyDocumentStatus.ACTIVE,
    )
    return repository


@pytest.fixture
def service(
    text_extractor: Mock,
    chunker: Mock,
    embedding_client: AsyncMock,
    policy_documents: AsyncMock,
) -> PolicyIngestionService:
    """Build the service under test from its fully mocked collaborators."""
    return PolicyIngestionService(
        text_extractor=text_extractor,
        chunker=chunker,
        embedding_client=embedding_client,
        policy_documents=policy_documents,
    )


async def should_activate_the_document_with_its_embedded_chunks(
    service: PolicyIngestionService,
    text_extractor: Mock,
    chunker: Mock,
    embedding_client: AsyncMock,
    policy_documents: AsyncMock,
) -> None:
    """Extract, chunk, embed every chunk, then activate the document."""
    result = await service.ingest(filename=FILENAME, content=CONTENT)

    text_extractor.extract_text.assert_called_once_with(content=CONTENT)
    chunker.chunk.assert_called_once_with(DOCUMENT_TEXT)
    embedding_client.embed_batch.assert_awaited_once_with([CHUNK_CONTENT])
    policy_documents.activate.assert_awaited_once_with(
        original_filename=FILENAME,
        chunks=[
            NewPolicyChunk(
                section_label=SECTION_LABEL,
                content=CHUNK_CONTENT,
                embedding=[0.1, 0.2, 0.3],
            )
        ],
    )
    assert result.chunk_count == 1
    assert result.status == PolicyDocumentStatus.ACTIVE
