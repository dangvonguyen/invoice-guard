"""Acceptance scenarios for listing an owner's invoices."""

from datetime import UTC, datetime, timedelta
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
    status: InvoiceStatus = InvoiceStatus.PROCESSING,
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


async def should_list_the_authenticated_employees_own_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Return an invoice the employee submitted."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get("/invoices", headers=employee_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["success"] is True
    assert [item["invoice_id"] for item in body["data"]] == [str(invoice.id)]


async def should_let_a_finance_reviewer_list_only_their_own_submissions(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    finance_reviewer: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Scope a reviewer's list to invoices they personally submitted."""
    await create_invoice(test_db, owner_id=employee.id, storage_key="employee.pdf")
    reviewer_invoice = await create_invoice(
        test_db, owner_id=finance_reviewer.id, storage_key="reviewer.pdf"
    )
    await test_db.commit()

    response = await client.get("/invoices", headers=reviewer_headers)

    body = response.json()
    assert [item["invoice_id"] for item in body["data"]] == [str(reviewer_invoice.id)]


async def should_reject_unauthenticated_listing(client: AsyncClient) -> None:
    """Require authentication before listing invoices."""
    response = await client.get("/invoices")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_order_invoices_newest_first(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Surface the most recently submitted invoice first."""
    now = datetime.now(UTC)
    oldest = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="oldest.pdf",
        created_at=now - timedelta(hours=2),
    )
    middle = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="middle.pdf",
        created_at=now - timedelta(hours=1),
    )
    newest = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="newest.pdf",
        created_at=now,
    )
    await test_db.commit()

    response = await client.get("/invoices", headers=employee_headers)

    body = response.json()
    assert [item["invoice_id"] for item in body["data"]] == [
        str(newest.id),
        str(middle.id),
        str(oldest.id),
    ]


async def should_exclude_invoices_with_a_failed_upload(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Never surface an internal upload_failed row to its owner."""
    await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="failed.pdf",
        status=InvoiceStatus.UPLOAD_FAILED,
    )
    visible = await create_invoice(
        test_db,
        owner_id=employee.id,
        storage_key="visible.pdf",
    )
    await test_db.commit()

    response = await client.get("/invoices", headers=employee_headers)

    body = response.json()
    assert [item["invoice_id"] for item in body["data"]] == [str(visible.id)]
