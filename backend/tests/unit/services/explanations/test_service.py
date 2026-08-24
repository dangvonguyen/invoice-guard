from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.core.errors import ForbiddenError, NotFoundError
from app.database.models.explanation import Explanation
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.policy_document import PolicyDocChunk, PolicyDocument
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.schemas.explanation import CitationView
from app.services.explanations.generation import GeneratedExplanation
from app.services.explanations.service import (
    ExplanationService,
    NoActivePolicyDocumentError,
    RuleNotExplainableError,
)
from app.services.rules.result import RuleCode

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

GENERATION_MODEL = "gpt-5-mini"
RETRIEVAL_TOP_K = 5

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REVIEWER_ID = UUID("00000000-0000-0000-0000-000000000010")
INVOICE_ID = UUID("10000000-0000-0000-0000-000000000001")
RULE_RESULT_ID = UUID("20000000-0000-0000-0000-000000000001")
CHUNK_ID = UUID("30000000-0000-0000-0000-000000000001")

STORED_RULE_RESULTS: list[InvoiceRuleResult] = [
    InvoiceRuleResult(
        id=RULE_RESULT_ID,
        invoice_id=INVOICE_ID,
        rule_code=RuleCode.CURRENCY_ALLOWED.value,
        outcome=RuleOutcome.FAIL,
        evidence={
            "currency": "CHF",
            "allowed_currencies": ["EUR", "GBP", "USD"],
        },
        evaluated_at=datetime(2000, 1, 1, tzinfo=UTC),
    )
]
STORED_INVOICE = Invoice(
    id=INVOICE_ID,
    owner_id=OWNER_ID,
    status=InvoiceStatus.AWAITING_REVIEW,
    storage_key="invoice.pdf",
    original_filename="invoice.pdf",
    created_at=datetime(2000, 1, 1, tzinfo=UTC),
    rule_results=STORED_RULE_RESULTS,
)
RETRIEVED_CHUNK = PolicyDocChunk(
    id=CHUNK_ID,
    policy_document_id=uuid4(),
    chunk_index=10,
    section_label="5.3 Allowed Currencies",
    content="Expenses must be submitted in USD, EUR, or GBP.",
    embedding=[0.1] * 1536,
)
ACTIVE_POLICY_DOCUMENT = PolicyDocument(
    id=uuid4(),
    original_filename="handbook.pdf",
    created_at=datetime(2000, 1, 1, tzinfo=UTC),
)
CITED_NARRATIVE = "The invoice's currency isn't on the handbook's allowed list."
PERSISTED_EXPLANATION = Explanation(
    id=uuid4(),
    rule_result_id=RULE_RESULT_ID,
    narrative=CITED_NARRATIVE,
    citations=[
        {
            "chunk_id": str(CHUNK_ID),
            "section_label": "5.3 Allowed Currencies",
            "content": "Expenses must be submitted in USD, EUR, or GBP.",
        }
    ],
    created_at=datetime(2000, 1, 1, tzinfo=UTC),
)


@dataclass(frozen=True)
class ExplanationContext:
    """Expose the service and collaborator roles used by each scenario."""

    service: ExplanationService
    invoice_repo: AsyncMock
    policy_repo: AsyncMock
    explanation_repo: AsyncMock
    embedding_client: AsyncMock
    generation_client: AsyncMock


@pytest.fixture
def context() -> ExplanationContext:
    invoice_repo = AsyncMock()
    invoice_repo.get_for_review_view.return_value = STORED_INVOICE
    policy_repo = AsyncMock()
    policy_repo.get_active_document.return_value = ACTIVE_POLICY_DOCUMENT
    policy_repo.search_similar_chunks.return_value = [RETRIEVED_CHUNK]
    explanation_repo = AsyncMock()
    explanation_repo.get_by_rule_result.return_value = None
    explanation_repo.create.return_value = PERSISTED_EXPLANATION
    embedding_client = AsyncMock()
    embedding_client.embed_batch.return_value = [[0.1, 0.2, 0.3]]
    generation_client = AsyncMock()
    generation_client.generate_explanation.return_value = GeneratedExplanation(
        narrative=CITED_NARRATIVE,
        cited_chunk_indexes=[0],
    )

    service = ExplanationService(
        invoice_repo=invoice_repo,
        policy_repo=policy_repo,
        explanation_repo=explanation_repo,
        embedding_client=embedding_client,
        generation_client=generation_client,
        generation_model=GENERATION_MODEL,
        retrieval_top_k=RETRIEVAL_TOP_K,
    )

    return ExplanationContext(
        service=service,
        invoice_repo=invoice_repo,
        policy_repo=policy_repo,
        explanation_repo=explanation_repo,
        embedding_client=embedding_client,
        generation_client=generation_client,
    )


async def should_generate_an_explanation_grounded_in_the_retrieved_chunks(
    context: ExplanationContext,
) -> None:
    """Retrieve policy chunks, generate a grounded explanation, and return it."""
    result = await context.service.resolve(
        invoice_id=INVOICE_ID,
        rule_code=RuleCode.CURRENCY_ALLOWED,
        reviewer_id=REVIEWER_ID,
    )

    assert result.explanation == CITED_NARRATIVE
    assert result.citations == [
        CitationView(
            chunk_id=CHUNK_ID,
            section_label="5.3 Allowed Currencies",
            content="Expenses must be submitted in USD, EUR, or GBP.",
        )
    ]
    context.embedding_client.embed_batch.assert_awaited_once()
    context.generation_client.generate_explanation.assert_awaited_once()


async def should_raise_not_found_when_no_failed_flag_matches_the_rule_code(
    context: ExplanationContext,
) -> None:
    """The invoice has no FAIL result for the requested rule code."""
    with pytest.raises(NotFoundError):
        await context.service.resolve(
            invoice_id=INVOICE_ID,
            rule_code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
            reviewer_id=REVIEWER_ID,
        )


async def should_raise_rule_not_explainable_for_a_non_explainable_rule_code(
    context: ExplanationContext,
) -> None:
    """The rule code isn't backed by a policy-configured threshold."""
    with pytest.raises(RuleNotExplainableError):
        await context.service.resolve(
            invoice_id=INVOICE_ID,
            rule_code=RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
            reviewer_id=REVIEWER_ID,
        )


async def should_raise_no_active_policy_document_without_generating(
    context: ExplanationContext,
) -> None:
    """No policy document has ever been ingested, so fail before generating."""
    context.policy_repo.get_active_document.return_value = None

    with pytest.raises(NoActivePolicyDocumentError):
        await context.service.resolve(
            invoice_id=INVOICE_ID,
            rule_code=RuleCode.CURRENCY_ALLOWED,
            reviewer_id=REVIEWER_ID,
        )

    context.generation_client.generate_explanation.assert_not_called()


async def should_return_the_cached_explanation_without_regenerating(
    context: ExplanationContext,
) -> None:
    """A previously persisted explanation is returned as-is, skipping generation."""
    context.explanation_repo.get_by_rule_result.return_value = PERSISTED_EXPLANATION

    await context.service.resolve(
        invoice_id=INVOICE_ID,
        rule_code=RuleCode.CURRENCY_ALLOWED,
        reviewer_id=REVIEWER_ID,
    )

    context.policy_repo.get_active_document.assert_not_called()
    context.generation_client.generate_explanation.assert_not_called()


async def should_raise_cannot_explain_own_invoice_for_the_owning_reviewer(
    context: ExplanationContext,
) -> None:
    """A reviewer requesting an explanation for their own submission is blocked."""
    with pytest.raises(ForbiddenError):
        await context.service.resolve(
            invoice_id=INVOICE_ID,
            rule_code=RuleCode.CURRENCY_ALLOWED,
            reviewer_id=OWNER_ID,
        )

    context.policy_repo.get_active_document.assert_not_called()
    context.generation_client.generate_explanation.assert_not_called()
