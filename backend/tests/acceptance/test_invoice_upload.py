"""Acceptance scenarios for invoice intake."""

from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_access_token_codec
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

MAX_BYTES = 10 * 1024 * 1024


@pytest_asyncio.fixture
async def employee(test_db: AsyncSession) -> User:
    """Persist an employee and issue their bearer token."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="alice@example.com",
        hashed_password="unused-password-hash",
        name="Alice",
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def auth_headers(employee: User) -> dict[str, str]:
    """Bearer header authenticating for employee."""
    token = get_access_token_codec().issue(str(employee.id))
    return {"Authorization": f"Bearer {token}"}


def pdf_bytes(size: int) -> bytes:
    """Build a minimal PDF-shaped payload padded to an exact byte size."""
    header = b"%PDF-1.4\n"
    padding = b"0" * max(size - len(header), 0)
    return (header + padding)[:size]


async def should_accept_authenticated_employees_valid_pdf_as_pending_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    auth_headers: dict[str, str],
) -> None:
    """Accept a size-compliant PDF and return its pending invoice identity."""
    response = await client.post(
        "/invoices",
        headers=auth_headers,
        files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "pending"
    invoice_id = UUID(body["invoice_id"])

    stored = await test_db.get(Invoice, invoice_id)
    assert stored is not None
    assert stored.owner_id == employee.id
    assert stored.status == InvoiceStatus.PENDING
    assert stored.storage_key


async def should_reject_unauthenticated_upload(client: AsyncClient) -> None:
    """Require authentication before accepting an invoice upload."""
    response = await client.post(
        "/invoices",
        files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_oversized_file_without_creating_a_row(
    client: AsyncClient, test_db: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """Reject an oversized upload without persisting an invoice record."""
    response = await client.post(
        "/invoices",
        headers=auth_headers,
        files={"file": ("huge-scan.pdf", pdf_bytes(MAX_BYTES + 1), "application/pdf")},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert (await test_db.scalars(select(Invoice))).first() is None


async def should_reject_disallowed_mime_type_without_creating_a_row(
    client: AsyncClient, test_db: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """Reject an unsupported media type without persisting an invoice record."""
    response = await client.post(
        "/invoices",
        headers=auth_headers,
        files={"file": ("receipt.jpg", b"\xff\xd8\xff\xe0fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert (await test_db.scalars(select(Invoice))).first() is None
