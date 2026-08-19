"""Specify SQL-backed invoice-decision persistence behavior."""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.decision import InvoiceDecisionOutcome
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User, UserRole
from app.database.repositories.decision import (
    DecisionAlreadyExistsError,
    DecisionRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest.fixture
def repository(test_db: AsyncSession) -> DecisionRepository:
    """Return a decision repository using the test database session."""
    return DecisionRepository(session=test_db)


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the employee who owns invoices created in these scenarios."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000020"),
        email="decision-owner@example.com",
        hashed_password="unused-hash",
        name="Owner",
        role=UserRole.EMPLOYEE,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest_asyncio.fixture
async def reviewer(test_db: AsyncSession) -> User:
    """Persist the finance reviewer who decides invoices in these scenarios."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000021"),
        email="decision-reviewer@example.com",
        hashed_password="unused-hash",
        name="Reviewer",
        role=UserRole.FINANCE_REVIEWER,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest_asyncio.fixture
async def invoice(test_db: AsyncSession, owner: User) -> Invoice:
    """Persist an invoice awaiting review."""
    invoice = Invoice(
        owner_id=owner.id,
        storage_key="key.pdf",
        original_filename="invoice.pdf",
        status=InvoiceStatus.AWAITING_REVIEW,
    )
    test_db.add(invoice)
    await test_db.flush()
    return invoice


async def should_record_a_decision_and_transition_the_invoice(
    test_db: AsyncSession,
    repository: DecisionRepository,
    invoice: Invoice,
    reviewer: User,
) -> None:
    """Insert the decision row and move the invoice to the matching status."""
    decision = await repository.record(
        invoice_id=invoice.id,
        outcome=InvoiceDecisionOutcome.APPROVED,
        reason="Within policy.",
        decided_by_id=reviewer.id,
    )

    assert decision.outcome == InvoiceDecisionOutcome.APPROVED
    assert decision.reason == "Within policy."

    stored = await test_db.scalar(select(Invoice).where(Invoice.id == invoice.id))
    assert stored is not None
    assert stored.status == InvoiceStatus.APPROVED


async def should_raise_when_the_invoice_already_has_a_decision(
    repository: DecisionRepository, invoice: Invoice, reviewer: User
) -> None:
    """Refuse a second decision on the same invoice."""
    await repository.record(
        invoice_id=invoice.id,
        outcome=InvoiceDecisionOutcome.APPROVED,
        reason="Within policy.",
        decided_by_id=reviewer.id,
    )

    with pytest.raises(DecisionAlreadyExistsError):
        await repository.record(
            invoice_id=invoice.id,
            outcome=InvoiceDecisionOutcome.REJECTED,
            reason="Changed my mind.",
            decided_by_id=reviewer.id,
        )
