"""Specify SQL-backed rule-result persistence behavior."""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.database.models.user import User
from app.database.repositories.invoice import InvoiceRepository
from app.database.repositories.rule_result import RuleResultRepository
from app.services.rules.result import RuleCode, RuleResult

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns the invoice used in these scenarios."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000020"),
        email="owner-rules@example.com",
        hashed_password="unused-hash",
        name="Owner",
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest_asyncio.fixture
async def invoice(test_db: AsyncSession, owner: User) -> Invoice:
    """Persist an invoice for rule results to attach to."""
    repository = InvoiceRepository(session=test_db)
    return await repository.create_pending(
        owner_id=owner.id, storage_key="rules-key.pdf", original_filename="invoice.pdf"
    )


@pytest.fixture
def repository(test_db: AsyncSession) -> RuleResultRepository:
    """Return a rule-result repository using the test database session."""
    return RuleResultRepository(session=test_db)


RESULTS = [
    RuleResult(rule_code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT, outcome=RuleOutcome.PASS)
]


async def should_insert_one_row_per_rule_result_stamped_with_invoice_and_timestamp(
    test_db: AsyncSession, repository: RuleResultRepository, invoice: Invoice
) -> None:
    """Persist every rule's outcome, whatever it is, with the invoice's FK."""
    await repository.replace_for_invoice(invoice_id=invoice.id, results=RESULTS)

    stored = (
        (
            await test_db.execute(
                select(InvoiceRuleResult).where(
                    InvoiceRuleResult.invoice_id == invoice.id
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(stored) == len(RESULTS)
    assert all(row.invoice_id == invoice.id for row in stored)
    assert {row.rule_code for row in stored} == {code.value for code in RuleCode}
