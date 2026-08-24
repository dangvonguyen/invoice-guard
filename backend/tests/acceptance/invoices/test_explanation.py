"""Acceptance scenarios for on-demand review-flag explanation generation."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_embedding_client, get_generation_client
from app.database.models.invoice import Invoice
from app.database.models.policy_document import EMBEDDING_DIMENSIONS
from app.database.models.rule_result import RuleOutcome
from app.database.models.user import User
from app.database.repositories.policy_document import (
    NewPolicyChunk,
    PolicyDocumentRepository,
)
from app.main import app
from app.services.explanations.generation import GeneratedExplanation
from tests.support.helpers import add_rule_result, create_invoice

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

CITED_NARRATIVE = "The invoice's currency isn't on the handbook's allowed list."


class FakeEmbeddingClient:
    """Stand in for the embedding-provider boundary with a fixed vector."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]


@dataclass
class FakeGenerationClient:
    """Stand in for the generation-provider boundary."""

    async def generate_explanation(
        self, *, summary: str, evidence: dict[str, Any], chunks: list[Any]
    ) -> GeneratedExplanation:
        return GeneratedExplanation(narrative=CITED_NARRATIVE, cited_chunk_indexes=[0])


@pytest.fixture
def fake_generation() -> None:
    app.dependency_overrides[get_generation_client] = FakeGenerationClient


@pytest.fixture
def fake_embeddings() -> None:
    app.dependency_overrides[get_embedding_client] = FakeEmbeddingClient


@pytest_asyncio.fixture
async def active_policy_document(test_db: AsyncSession) -> None:
    """Activate a one-chunk policy document so retrieval has something to find."""
    repository = PolicyDocumentRepository(session=test_db)
    await repository.activate(
        original_filename="handbook-v1.pdf",
        chunks=[
            NewPolicyChunk(
                section_label="5.3 Allowed Currencies",
                content="Expenses must be submitted in USD, EUR, or GBP.",
                embedding=[0.0] * EMBEDDING_DIMENSIONS,
            ),
        ],
    )
    await test_db.commit()


@pytest_asyncio.fixture
async def employee_invoice(test_db: AsyncSession, employee: User) -> Invoice:
    """Persist an invoice owned by the employee, with a failed currency flag."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await add_rule_result(
        test_db,
        invoice_id=invoice.id,
        outcome=RuleOutcome.FAIL,
        rule_code="currency_allowed",
        evidence={"currency": "CHF", "allowed_currencies": ["EUR", "GBP", "USD"]},
    )
    await test_db.commit()
    return invoice


def explanation_url(invoice_id: UUID, rule_code: str) -> str:
    return f"/invoices/{invoice_id}/flags/{rule_code}/explanation"


@pytest.mark.usefixtures("fake_generation", "fake_embeddings", "active_policy_document")
async def should_generate_and_persist_an_explanation_for_an_explainable_flag(
    client: AsyncClient,
    employee_invoice: Invoice,
    reviewer_headers: dict[str, str],
) -> None:
    """Retrieve policy chunks, generate a grounded explanation, and return it."""
    response = await client.post(
        explanation_url(employee_invoice.id, "currency_allowed"),
        headers=reviewer_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()["data"]
    assert body["explanation"] == CITED_NARRATIVE
    assert body["citations"][0]["content"] == (
        "Expenses must be submitted in USD, EUR, or GBP."
    )
