"""Specify SQL-backed invoice-decision persistence behavior."""

import asyncio
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.database.models.decision import InvoiceDecision, InvoiceDecisionOutcome
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User, UserRole
from app.database.repositories.decision import (
    DecisionAlreadyExistsError,
    DecisionRepository,
    InvoiceNotAwaitingReviewError,
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


async def should_raise_when_the_invoice_is_not_awaiting_review(
    test_db: AsyncSession,
    repository: DecisionRepository,
    owner: User,
    reviewer: User,
) -> None:
    """Refuse a decision on an invoice that never reached the review queue."""
    invoice = Invoice(
        owner_id=owner.id,
        storage_key="processing.pdf",
        original_filename="processing.pdf",
        status=InvoiceStatus.PROCESSING,
    )
    test_db.add(invoice)
    await test_db.flush()

    with pytest.raises(InvoiceNotAwaitingReviewError):
        await repository.record(
            invoice_id=invoice.id,
            outcome=InvoiceDecisionOutcome.APPROVED,
            reason="Within policy.",
            decided_by_id=reviewer.id,
        )


async def should_let_only_one_of_two_concurrent_decisions_succeed(
    test_engine: AsyncEngine,
) -> None:
    """Two independent connections racing to decide the same invoice.

    Committed directly against `test_engine` (bypassing the shared,
    never-truly-committed `test_connection`), so the two sessions are on
    genuinely separate connections and can actually race. Cleans up its
    own rows since nothing here rolls back automatically.
    """
    sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)

    async with sessionmaker() as setup:
        owner = User(
            email="race-owner@example.com",
            hashed_password="unused-hash",
            name="Race Owner",
            role=UserRole.EMPLOYEE,
        )
        reviewer = User(
            email="race-reviewer@example.com",
            hashed_password="unused-hash",
            name="Race Reviewer",
            role=UserRole.FINANCE_REVIEWER,
        )
        setup.add_all([owner, reviewer])
        await setup.flush()
        invoice = Invoice(
            owner_id=owner.id,
            storage_key="race.pdf",
            original_filename="race.pdf",
            status=InvoiceStatus.AWAITING_REVIEW,
        )
        setup.add(invoice)
        await setup.commit()

    async def attempt(outcome: InvoiceDecisionOutcome) -> bool:
        async with sessionmaker() as session:
            repo = DecisionRepository(session=session)
            try:
                await repo.record(
                    invoice_id=invoice.id,
                    outcome=outcome,
                    reason="race",
                    decided_by_id=reviewer.id,
                )
                return True
            except DecisionAlreadyExistsError:
                return False

    try:
        results = await asyncio.gather(
            attempt(InvoiceDecisionOutcome.APPROVED),
            attempt(InvoiceDecisionOutcome.REJECTED),
        )

        assert sorted(results) == [False, True]

        async with sessionmaker() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(InvoiceDecision)
                .where(InvoiceDecision.invoice_id == invoice.id)
            )
            assert count == 1
    finally:
        async with sessionmaker() as cleanup:
            await cleanup.execute(
                delete(Invoice).where(Invoice.id == invoice.id),
            )
            await cleanup.execute(
                delete(User).where(User.id.in_([owner.id, reviewer.id])),
            )
            await cleanup.commit()
