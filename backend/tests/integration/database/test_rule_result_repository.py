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
from tests.support.helpers import create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns the invoice used in these scenarios."""
    return await create_user(
        test_db,
        id=UUID("00000000-0000-0000-0000-000000000020"),
        email="owner-rules@example.com",
    )


@pytest_asyncio.fixture
async def invoice(test_db: AsyncSession, owner: User) -> Invoice:
    """Persist an invoice for rule results to attach to."""
    repository = InvoiceRepository(session=test_db)
    return await repository.create_processing(
        owner_id=owner.id, storage_key="rules-key.pdf", original_filename="invoice.pdf"
    )


@pytest.fixture
def repository(test_db: AsyncSession) -> RuleResultRepository:
    """Return a rule-result repository using the test database session."""
    return RuleResultRepository(session=test_db)


RESULTS = [
    RuleResult(
        rule_code=RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
        outcome=RuleOutcome.PASS,
    ),
    RuleResult(
        rule_code=RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
        outcome=RuleOutcome.NOT_APPLICABLE,
        evidence={},
    ),
    RuleResult(
        rule_code=RuleCode.CURRENCY_ALLOWED,
        outcome=RuleOutcome.FAIL,
        evidence={"currency": "CHF", "allowed_currencies": ["EUR", "GBP", "USD"]},
    ),
    RuleResult(
        rule_code=RuleCode.INVOICE_DATE_NOT_IN_FUTURE,
        outcome=RuleOutcome.PASS,
    ),
    RuleResult(
        rule_code=RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW,
        outcome=RuleOutcome.PASS,
    ),
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


async def should_delete_prior_rows_before_inserting_the_new_set(
    test_db: AsyncSession, repository: RuleResultRepository, invoice: Invoice
) -> None:
    """Replace, never accumulate, rows across a retried evaluation."""
    await repository.replace_for_invoice(invoice_id=invoice.id, results=RESULTS)

    updated_results = [
        RuleResult(rule_code=code, outcome=RuleOutcome.PASS) for code in RuleCode
    ]
    await repository.replace_for_invoice(invoice_id=invoice.id, results=updated_results)

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
    assert all(row.outcome == RuleOutcome.PASS for row in stored)


async def should_leave_zero_rows_when_handed_an_empty_list(
    test_db: AsyncSession, repository: RuleResultRepository, invoice: Invoice
) -> None:
    """Persist nothing for an invoice that was never evaluated."""
    await repository.replace_for_invoice(invoice_id=invoice.id, results=[])

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

    assert stored == []


async def should_return_an_empty_sequence_for_an_invoice_never_evaluated(
    repository: RuleResultRepository, invoice: Invoice
) -> None:
    """Return no rows for an invoice that was never evaluated."""
    rows = await repository.list_by_invoice(invoice.id)

    assert rows == []


async def should_cascade_delete_rule_results_when_the_invoice_is_deleted(
    test_db: AsyncSession, repository: RuleResultRepository, invoice: Invoice
) -> None:
    """Delete an invoice's rule-result rows rather than orphan or FK-error."""
    await repository.replace_for_invoice(invoice_id=invoice.id, results=RESULTS)

    await test_db.delete(invoice)
    await test_db.flush()

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
    assert stored == []
