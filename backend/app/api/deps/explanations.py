"""Dependencies for on-demand review-flag explanation generation."""

from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.services.explanations.generation import (
    GenerationClient,
    OpenAIGenerationClient,
)
from app.services.explanations.service import ExplanationService

from .invoices import InvoiceRepositoryDep
from .policies import EmbeddingClientDep, PolicyDocumentRepositoryDep, get_openai_client


def get_generation_client() -> GenerationClient:
    """Create the generation client."""
    settings = get_settings()
    return OpenAIGenerationClient(
        client=get_openai_client(),
        model=settings.OPENAI_GENERATION_MODEL,
    )


GenerationClientDep = Annotated[GenerationClient, Depends(get_generation_client)]


def get_explanation_service(
    invoice_repo: InvoiceRepositoryDep,
    policy_repo: PolicyDocumentRepositoryDep,
    embedding_client: EmbeddingClientDep,
    generation_client: GenerationClientDep,
) -> ExplanationService:
    """Create the explanation service from its injected dependencies."""
    settings = get_settings()
    return ExplanationService(
        invoice_repo=invoice_repo,
        policy_repo=policy_repo,
        embedding_client=embedding_client,
        generation_client=generation_client,
        generation_model=settings.OPENAI_GENERATION_MODEL,
        retrieval_top_k=settings.EXPLANATION_RETRIEVAL_TOP_K,
    )


ExplanationServiceDep = Annotated[ExplanationService, Depends(get_explanation_service)]
