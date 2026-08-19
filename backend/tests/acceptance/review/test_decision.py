"""Acceptance scenarios for recording a finance reviewer's final decision."""

from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice, InvoiceStatus
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
) -> Invoice:
    """Insert an invoice row directly, bypassing upload and processing."""
    invoice = Invoice(
        owner_id=owner_id,
        storage_key=storage_key,
        original_filename=storage_key,
        status=status,
    )
    test_db.add(invoice)
    await test_db.flush()
    return invoice


async def should_record_an_approval_and_transition_the_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
    finance_reviewer: User,
) -> None:
    """Approve an invoice and durably move it to the approved status."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json={"outcome": "approved", "reason": "Within policy."},
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()["data"]
    assert body["outcome"] == "approved"
    assert body["reason"] == "Within policy."
    assert body["decided_by"] == finance_reviewer.name

    await test_db.refresh(invoice)
    assert invoice.status == InvoiceStatus.APPROVED


async def should_record_a_rejection_and_transition_the_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Reject an invoice and durably move it to the rejected status."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json={"outcome": "rejected", "reason": "Missing receipt."},
    )

    assert response.status_code == status.HTTP_201_CREATED

    await test_db.refresh(invoice)
    assert invoice.status == InvoiceStatus.REJECTED


async def should_let_the_employee_see_the_final_decision(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
    reviewer_headers: dict[str, str],
) -> None:
    """Surface the reviewer's outcome and reason back to the invoice owner."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()
    await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json={"outcome": "approved", "reason": "Within policy."},
    )

    response = await client.get(f"/invoices/{invoice.id}", headers=employee_headers)

    body = response.json()["data"]
    assert body["status"] == "approved"
    assert body["decision"]["outcome"] == "approved"
    assert body["decision"]["reason"] == "Within policy."


async def should_reject_employees_from_deciding(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Require the finance_reviewer role to record a decision."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=employee_headers,
        json={"outcome": "approved", "reason": "Within policy."},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def should_reject_unauthenticated_decisions(
    client: AsyncClient, test_db: AsyncSession, employee: User
) -> None:
    """Require authentication before recording a decision."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        json={"outcome": "approved", "reason": "Within policy."},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
