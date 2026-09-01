"""Dependencies for on-demand review-flag explanation generation."""

from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.database.repositories.explanation import ExplanationRepository
from app.database.repositories.invoice import InvoiceRepository
from app.services.explanations.generation import (
    GenerationClient,
    build_generation_client,
)
from app.services.explanations.service import ExplanationService

from .policies import EmbeddingClientDep, PolicyDocumentRepositoryDep
from .sessions import SessionDep


def get_generation_client() -> GenerationClient:
    """Create the generation client."""
    settings = get_settings()
    return build_generation_client(
        provider=settings.GENERATION_PROVIDER,
        model=settings.GENERATION_MODEL,
        max_tokens=settings.GENERATION_MAX_TOKENS,
    )


GenerationClientDep = Annotated[GenerationClient, Depends(get_generation_client)]


def get_explanation_repository(session: SessionDep) -> ExplanationRepository:
    """Create an explanation repository configured with the database session."""
    return ExplanationRepository(session=session)


ExplanationRepositoryDep = Annotated[
    ExplanationRepository, Depends(get_explanation_repository)
]


def get_explanation_invoice_repository(session: SessionDep) -> InvoiceRepository:
    """Create an invoice repository for explanation lookups.

    Explanation resolution only reads the invoice, so it shares the
    request's default auto-committing session (see `SessionDep`) rather
    than the upload flow's manually-controlled one — mixing the two here
    would nest the explanation write's transaction inside a session that
    never commits its own read, rolling the write back on cleanup.
    """
    return InvoiceRepository(session=session)


ExplanationInvoiceRepositoryDep = Annotated[
    InvoiceRepository, Depends(get_explanation_invoice_repository)
]


def get_explanation_service(
    invoice_repo: ExplanationInvoiceRepositoryDep,
    policy_repo: PolicyDocumentRepositoryDep,
    explanation_repo: ExplanationRepositoryDep,
    embedding_client: EmbeddingClientDep,
    generation_client: GenerationClientDep,
) -> ExplanationService:
    """Create the explanation service from its injected dependencies."""
    settings = get_settings()
    return ExplanationService(
        invoice_repo=invoice_repo,
        policy_repo=policy_repo,
        explanation_repo=explanation_repo,
        embedding_client=embedding_client,
        generation_client=generation_client,
        retrieval_top_k=settings.EXPLANATION_RETRIEVAL_TOP_K,
    )


ExplanationServiceDep = Annotated[ExplanationService, Depends(get_explanation_service)]
