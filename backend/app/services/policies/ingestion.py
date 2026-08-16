"""Coordinate text extraction, chunking, embedding, and activation."""

from dataclasses import dataclass
from uuid import UUID

from app.database.models.policy_document import PolicyDocumentStatus
from app.database.repositories.policy_document import (
    NewPolicyChunk,
    PolicyDocumentRepository,
)
from app.services.embeddings.client import EmbeddingClient
from app.services.extraction.text import TextExtractor
from app.services.policies.chunking import Chunker
from app.services.upload.validation import UploadValidator


@dataclass(frozen=True)
class IngestResult:
    """One ingestion attempt's persisted-worthy outcome."""

    document_id: UUID
    status: PolicyDocumentStatus
    chunk_count: int


class PolicyIngestionService:
    """Turn an uploaded handbook PDF into an active, embedded, chunked document."""

    def __init__(
        self,
        *,
        validator: UploadValidator,
        text_extractor: TextExtractor,
        chunker: Chunker,
        embedding_client: EmbeddingClient,
        policy_documents: PolicyDocumentRepository,
    ) -> None:
        self._validator = validator
        self._text_extractor = text_extractor
        self._chunker = chunker
        self._embedding_client = embedding_client
        self._policy_documents = policy_documents

    async def ingest(
        self,
        *,
        filename: str,
        content_type: str | None,
        content_length: int | None,
        content: bytes,
    ) -> IngestResult:
        """Ingest a handbook PDF's bytes and activate it as the current policy."""
        self._validator.validate(
            filename=filename,
            content_type=content_type,
            content_length=content_length,
            content=content,
        )

        document_text = self._text_extractor.extract_text(content=content)
        chunks = self._chunker.chunk(document_text)

        embeddings = await self._embedding_client.embed_batch(
            [chunk.content for chunk in chunks]
        )

        document = await self._policy_documents.activate(
            original_filename=filename,
            chunks=[
                NewPolicyChunk(
                    section_label=chunk.label,
                    content=chunk.content,
                    embedding=embedding,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ],
        )

        return IngestResult(
            document_id=document.id, status=document.status, chunk_count=len(chunks)
        )
