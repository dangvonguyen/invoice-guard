"""Acceptance scenarios for the finance reviewer's review queue."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.database.models.user import User

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


async def create_invoice(
    test_db: AsyncSession,
    *,
    owner_id: UUID,
    storage_key: str = "invoice.pdf",
    status: InvoiceStatus = InvoiceStatus.AWAITING_REVIEW,
    created_at: datetime | None = None,
) -> Invoice:
    """Insert an invoice row directly, bypassing upload and processing."""
    invoice = Invoice(
        owner_id=owner_id,
        storage_key=storage_key,
        original_filename=storage_key,
        status=status,
        **({"created_at": created_at} if created_at is not None else {}),
    )
    test_db.add(invoice)
    await test_db.flush()
    return invoice


async def add_rule_result(
    test_db: AsyncSession, *, invoice_id: UUID, outcome: RuleOutcome
) -> None:
    test_db.add(
        InvoiceRuleResult(
            invoice_id=invoice_id, rule_code="currency_allowed", outcome=outcome
        )
    )
    await test_db.flush()


async def should_list_awaiting_review_invoices_oldest_first(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Surface the longest-waiting invoice first."""
    now = datetime.now(UTC)
    older = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="older.pdf",
        created_at=now - timedelta(hours=1),
    )
    newer = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="newer.pdf",
        created_at=now,
    )
    await test_db.commit()

    response = await client.get("/review-queue", headers=reviewer_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["success"] is True
    assert [item["id"] for item in body["data"]] == [str(older.id), str(newer.id)]


async def should_exclude_invoices_not_awaiting_review(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Never surface an invoice still processing or already decided."""
    await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="processing.pdf",
        status=InvoiceStatus.PROCESSING,
    )
    visible = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="visible.pdf",
        status=InvoiceStatus.AWAITING_REVIEW,
    )
    await test_db.commit()

    response = await client.get("/review-queue", headers=reviewer_headers)

    body = response.json()
    assert [item["id"] for item in body["data"]] == [str(visible.id)]


async def should_report_the_number_of_failed_checks_as_the_flag_count(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Count only FAIL rule results toward an invoice's flag count."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await add_rule_result(test_db, invoice_id=invoice.id, outcome=RuleOutcome.FAIL)
    await add_rule_result(test_db, invoice_id=invoice.id, outcome=RuleOutcome.FAIL)
    await add_rule_result(test_db, invoice_id=invoice.id, outcome=RuleOutcome.PASS)
    await test_db.commit()

    response = await client.get("/review-queue", headers=reviewer_headers)

    body = response.json()
    assert body["data"][0]["flag_count"] == 2


async def should_reject_employees_from_the_review_queue(
    client: AsyncClient, employee_headers: dict[str, str]
) -> None:
    """Require the finance_reviewer role to browse the queue."""
    response = await client.get("/review-queue", headers=employee_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def should_reject_unauthenticated_access(client: AsyncClient) -> None:
    """Require authentication before browsing the queue."""
    response = await client.get("/review-queue")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
