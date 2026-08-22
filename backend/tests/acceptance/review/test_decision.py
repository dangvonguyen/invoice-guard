"""Acceptance scenarios for recording a finance reviewer's final decision."""

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User
from tests.support.helpers import create_invoice

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

APPROVAL_PAYLOAD = {"outcome": "approved", "reason": "Within policy."}


@pytest_asyncio.fixture
async def invoice(test_db: AsyncSession, employee: User) -> Invoice:
    """Persist an invoice awaiting review, owned by the employee."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()
    return invoice


async def should_record_an_approval_and_transition_the_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    invoice: Invoice,
    reviewer_headers: dict[str, str],
    finance_reviewer: User,
) -> None:
    """Approve an invoice and durably move it to the approved status."""
    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json=APPROVAL_PAYLOAD,
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
    invoice: Invoice,
    reviewer_headers: dict[str, str],
) -> None:
    """Reject an invoice and durably move it to the rejected status."""
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
    invoice: Invoice,
    employee_headers: dict[str, str],
    reviewer_headers: dict[str, str],
) -> None:
    """Surface the reviewer's outcome and reason back to the invoice owner."""
    await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json=APPROVAL_PAYLOAD,
    )

    response = await client.get(f"/invoices/{invoice.id}", headers=employee_headers)

    body = response.json()["data"]
    assert body["status"] == "approved"
    assert body["decision"]["outcome"] == "approved"
    assert body["decision"]["reason"] == "Within policy."


async def should_reject_a_second_decision_on_the_same_invoice(
    client: AsyncClient,
    invoice: Invoice,
    reviewer_headers: dict[str, str],
) -> None:
    """Return 409 when an invoice already carries a final decision."""
    first = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json=APPROVAL_PAYLOAD,
    )
    assert first.status_code == status.HTTP_201_CREATED

    second = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json={"outcome": "rejected", "reason": "Changed my mind."},
    )

    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["error"]["code"] == "INVOICE_ALREADY_DECIDED"


async def should_reject_deciding_an_invoice_that_is_not_awaiting_review(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Refuse a decision on an invoice that never reached the review queue."""
    invoice = await create_invoice(
        test_db, owner_id=employee.id, status=InvoiceStatus.PROCESSING
    )
    await test_db.commit()

    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=reviewer_headers,
        json=APPROVAL_PAYLOAD,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"]["code"] == "INVOICE_NOT_AWAITING_REVIEW"


async def should_reject_employees_from_deciding(
    client: AsyncClient,
    invoice: Invoice,
    employee_headers: dict[str, str],
) -> None:
    """Require the finance_reviewer role to record a decision."""
    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        headers=employee_headers,
        json=APPROVAL_PAYLOAD,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def should_reject_unauthenticated_decisions(
    client: AsyncClient, invoice: Invoice
) -> None:
    """Require authentication before recording a decision."""
    response = await client.post(
        f"/invoices/{invoice.id}/decision",
        json=APPROVAL_PAYLOAD,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_a_reviewer_deciding_on_their_own_submission(
    client: AsyncClient,
    test_db: AsyncSession,
    finance_reviewer: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Block self-approval even when the reviewer knows their own invoice's id."""
    own_invoice = await create_invoice(test_db, owner_id=finance_reviewer.id)
    await test_db.commit()

    response = await client.post(
        f"/invoices/{own_invoice.id}/decision",
        headers=reviewer_headers,
        json=APPROVAL_PAYLOAD,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "CANNOT_DECIDE_OWN_INVOICE"

    await test_db.refresh(own_invoice)
    assert own_invoice.status == InvoiceStatus.AWAITING_REVIEW
