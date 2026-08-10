"""Acceptance scenarios for invoice intake."""

from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_access_token_codec
from app.database.models.user import User

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def authenticated_employee(test_db: AsyncSession) -> tuple[User, str]:
    """Persist an employee and issue their bearer token."""
    employee = User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="alice@example.com",
        hashed_password="unused-password-hash",
        name="Alice",
    )
    test_db.add(employee)
    await test_db.flush()

    token = get_access_token_codec().issue(str(employee.id))
    return employee, token


async def should_accept_authenticated_employees_valid_pdf_as_pending_invoice(
    client: AsyncClient,
    authenticated_employee: tuple[User, str],
) -> None:
    """Accept a size-compliant PDF and return its pending invoice identity."""
    _employee, token = authenticated_employee
    pdf_prefix = b"%PDF-1.4\ninvoice content\n"
    pdf = pdf_prefix + b" " * (240 * 1024 - len(pdf_prefix))

    response = await client.post(
        "/invoices",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invoice.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert set(body) == {"invoice_id", "status"}
    assert UUID(body["invoice_id"])
    assert body["status"] == "pending"
