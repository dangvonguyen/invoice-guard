"""Acceptance scenarios for on-demand review-flag explanation generation."""

from dataclasses import dataclass, field
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

    calls: list[Any] = field(default_factory=list)
    model: str = "gpt-5"

    async def generate_explanation(
        self, *, summary: str, evidence: dict[str, Any], chunks: list[Any]
    ) -> GeneratedExplanation:
        self.calls.append((summary, evidence, chunks))
        return GeneratedExplanation(narrative=CITED_NARRATIVE, cited_chunk_indexes=[0])


@pytest.fixture
def fake_generation() -> FakeGenerationClient:
    fake = FakeGenerationClient()
    app.dependency_overrides[get_generation_client] = lambda: fake
    return fake


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


async def should_reject_when_no_failed_flag_matches_the_rule_code(
    client: AsyncClient,
    employee_invoice: Invoice,
    reviewer_headers: dict[str, str],
) -> None:
    """No FAIL result for that rule code exists on the invoice, so 404."""
    response = await client.post(
        explanation_url(employee_invoice.id, "expense_within_amount_limit"),
        headers=reviewer_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.usefixtures("fake_embeddings", "active_policy_document")
async def should_return_the_previously_persisted_explanation_on_a_second_request(
    client: AsyncClient,
    employee_invoice: Invoice,
    reviewer_headers: dict[str, str],
    fake_generation: FakeGenerationClient,
) -> None:
    """A second request returns the cached explanation instead of regenerating."""
    first = await client.post(
        explanation_url(employee_invoice.id, "currency_allowed"),
        headers=reviewer_headers,
    )
    second = await client.post(
        explanation_url(employee_invoice.id, "currency_allowed"),
        headers=reviewer_headers,
    )

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert second.json()["data"] == first.json()["data"]
    assert len(fake_generation.calls) == 1


@pytest.mark.usefixtures("fake_generation", "fake_embeddings")
async def should_reject_explanation_requests_for_a_non_explainable_rule(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """A rule with no policy-backed threshold can't be explained, so reject it."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await add_rule_result(
        test_db,
        invoice_id=invoice.id,
        outcome=RuleOutcome.FAIL,
        rule_code="line_item_total_consistency",
        evidence={"stated_total": "100.00", "computed_total": "90.00"},
    )
    await test_db.commit()

    response = await client.post(
        explanation_url(invoice.id, "line_item_total_consistency"),
        headers=reviewer_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def should_reject_when_no_active_policy_document_exists(
    client: AsyncClient,
    employee_invoice: Invoice,
    reviewer_headers: dict[str, str],
) -> None:
    """No policy document has ever been ingested, so fail without generating."""
    response = await client.post(
        explanation_url(employee_invoice.id, "currency_allowed"),
        headers=reviewer_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def should_reject_a_reviewer_explaining_their_own_submission(
    client: AsyncClient,
    test_db: AsyncSession,
    finance_reviewer: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Block self-submission explanation requests, mirroring the decision endpoint."""
    own_invoice = await create_invoice(test_db, owner_id=finance_reviewer.id)
    await add_rule_result(
        test_db,
        invoice_id=own_invoice.id,
        outcome=RuleOutcome.FAIL,
        rule_code="currency_allowed",
        evidence={"currency": "CHF", "allowed_currencies": ["EUR", "GBP", "USD"]},
    )
    await test_db.commit()

    response = await client.post(
        explanation_url(own_invoice.id, "currency_allowed"),
        headers=reviewer_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "CANNOT_EXPLAIN_OWN_INVOICE"
