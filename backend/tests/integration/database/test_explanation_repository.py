"""Specify SQL-backed explanation persistence and cascade-delete behavior."""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.database.models.user import User
from app.database.repositories.explanation import ExplanationRepository
from app.database.repositories.invoice import InvoiceRepository
from app.database.repositories.rule_result import RuleResultRepository, RuleResultRow
from tests.support.helpers import create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]

CITATIONS = [
    {
        "chunk_id": "30000000-0000-0000-0000-000000000001",
        "section_label": "5.3 Allowed Currencies",
        "content": "Expenses must be submitted in USD, EUR, or GBP.",
    }
]


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns the invoice used in these scenarios."""
    return await create_user(
        test_db,
        id=UUID("00000000-0000-0000-0000-000000000030"),
        email="owner-explanations@example.com",
    )


@pytest_asyncio.fixture
async def invoice(test_db: AsyncSession, owner: User) -> Invoice:
    """Persist an invoice for a rule result to attach to."""
    repository = InvoiceRepository(session=test_db)
    return await repository.create_processing(
        owner_id=owner.id,
        storage_key="explanations-key.pdf",
        original_filename="invoice.pdf",
    )


@pytest_asyncio.fixture
async def rule_result(test_db: AsyncSession, invoice: Invoice) -> InvoiceRuleResult:
    """Persist a failed, explainable rule result for the invoice."""
    rule_results = RuleResultRepository(session=test_db)
    await rule_results.replace_for_invoice(
        invoice_id=invoice.id,
        results=[
            RuleResultRow(
                rule_code="currency_allowed",
                outcome=RuleOutcome.FAIL,
                evidence={
                    "currency": "CHF",
                    "allowed_currencies": ["EUR", "GBP", "USD"],
                },
            ),
        ],
    )
    [row] = await rule_results.list_by_invoice(invoice.id)
    return row


@pytest.fixture
def repository(test_db: AsyncSession) -> ExplanationRepository:
    """Return an explanation repository using the test database session."""
    return ExplanationRepository(session=test_db)


@pytest.fixture
def rule_results(test_db: AsyncSession) -> RuleResultRepository:
    """Return a rule-result repository using the test database session."""
    return RuleResultRepository(session=test_db)


async def should_persist_and_return_an_explanation_for_its_rule_result(
    repository: ExplanationRepository, rule_result: InvoiceRuleResult
) -> None:
    """Round-trip a generated explanation keyed to its rule-result row."""
    created = await repository.create(
        rule_result_id=rule_result.id,
        narrative="The invoice's currency isn't on the handbook's allowed list.",
        citations=CITATIONS,
    )

    fetched = await repository.get_by_rule_result(rule_result.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.narrative == created.narrative
    assert fetched.citations == CITATIONS


async def should_return_none_when_no_explanation_exists_for_the_rule_result(
    repository: ExplanationRepository, rule_result: InvoiceRuleResult
) -> None:
    """Report no cached explanation exists yet for a rule-result row."""
    fetched = await repository.get_by_rule_result(rule_result.id)

    assert fetched is None


async def should_cascade_delete_the_explanation_when_its_rule_result_is_replaced(
    repository: ExplanationRepository,
    rule_results: RuleResultRepository,
    invoice: Invoice,
    rule_result: InvoiceRuleResult,
) -> None:
    """Clear stale explanations when re-evaluation replaces the rule-result row."""
    await repository.create(
        rule_result_id=rule_result.id,
        narrative="The invoice's currency isn't on the handbook's allowed list.",
        citations=CITATIONS,
    )

    await rule_results.replace_for_invoice(
        invoice_id=invoice.id,
        results=[
            RuleResultRow(rule_code="currency_allowed", outcome=RuleOutcome.PASS),
        ],
    )

    fetched = await repository.get_by_rule_result(rule_result.id)
    assert fetched is None
