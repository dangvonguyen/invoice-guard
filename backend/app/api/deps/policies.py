"""Dependencies for policy document ingestion and listing."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from openai import AsyncOpenAI

from app.core.config import get_settings, unwrap_secret
from app.database.models.user import User, UserRole
from app.database.repositories.policy_document import PolicyDocumentRepository
from app.services.embeddings.client import EmbeddingClient, OpenAIEmbeddingClient
from app.services.extraction.text import PdfTextExtractor, TextExtractor
from app.services.policies.chunking import Chunker, SectionChunker
from app.services.policies.ingestion import PolicyIngestionService
from app.services.upload.validation import UploadValidator

from .auth import CurrentUser
from .sessions import SessionDep


async def get_current_finance_reviewer(current_user: CurrentUser) -> User:
    """Require the authenticated user to hold the finance_reviewer role."""
    if current_user.role != UserRole.FINANCE_REVIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="finance_reviewer role required",
        )
    return current_user


CurrentFinanceReviewer = Annotated[User, Depends(get_current_finance_reviewer)]


def get_policy_document_repository(session: SessionDep) -> PolicyDocumentRepository:
    """Create a policy document repository configured with the database session."""
    return PolicyDocumentRepository(session=session)


PolicyDocumentRepositoryDep = Annotated[
    PolicyDocumentRepository, Depends(get_policy_document_repository)
]


def get_policy_document_validator() -> UploadValidator:
    """Create the MIME/size validator, capped for policy handbook uploads."""
    settings = get_settings()
    return UploadValidator(max_bytes=settings.POLICY_DOCUMENT_MAX_BYTES)


PolicyDocumentValidatorDep = Annotated[
    UploadValidator, Depends(get_policy_document_validator)
]


def get_text_extractor() -> TextExtractor:
    """Create the PDF text-layer extractor, reused from invoice extraction."""
    return PdfTextExtractor()


TextExtractorDep = Annotated[TextExtractor, Depends(get_text_extractor)]


def get_chunker() -> Chunker:
    """Create the section/chunk splitter from the configured token budget."""
    settings = get_settings()
    return SectionChunker(
        min_tokens=settings.POLICY_CHUNK_MIN_TOKENS,
        max_tokens=settings.POLICY_CHUNK_MAX_TOKENS,
    )


ChunkerDep = Annotated[Chunker, Depends(get_chunker)]


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    """Return the shared async OpenAI client."""
    settings = get_settings()
    return AsyncOpenAI(api_key=unwrap_secret(settings.OPENAI_API_KEY))


def get_embedding_client() -> EmbeddingClient:
    """Create the embedding client, shared with the RAG explanation feature."""
    settings = get_settings()
    return OpenAIEmbeddingClient(
        client=get_openai_client(),
        model=settings.OPENAI_EMBEDDING_MODEL,
    )


EmbeddingClientDep = Annotated[EmbeddingClient, Depends(get_embedding_client)]


def get_policy_ingestion_service(
    validator: PolicyDocumentValidatorDep,
    text_extractor: TextExtractorDep,
    chunker: ChunkerDep,
    embedding_client: EmbeddingClientDep,
    policy_documents: PolicyDocumentRepositoryDep,
) -> PolicyIngestionService:
    """Create the policy ingestion service from its injected dependencies."""
    return PolicyIngestionService(
        validator=validator,
        text_extractor=text_extractor,
        chunker=chunker,
        embedding_client=embedding_client,
        policy_documents=policy_documents,
    )


PolicyIngestionServiceDep = Annotated[
    PolicyIngestionService, Depends(get_policy_ingestion_service)
]
