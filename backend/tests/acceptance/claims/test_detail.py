"""Acceptance scenarios for reading a single claim's detail and attachment."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorageClient
from app.database.models.user import User
from tests.support.helpers import create_claim

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


async def should_return_the_full_claim_to_its_owner(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Surface business context, invoice facts, status, and attachment info."""
    claim = await create_claim(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get(f"/claims/{claim.id}", headers=employee_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()["data"]
    assert body["id"] == str(claim.id)
    assert body["status"] == "submitted"
    assert body["expense_title"] == "Annual Figma subscription"
    assert body["business_purpose"] == "Design tooling for the product team."
    assert body["category"] == "software_hosting"
    assert body["cost_center"] == "PRODUCT-DESIGN"
    assert body["vendor"] == "Figma Inc."
    assert body["invoice_number"] == "FIG-2026-00417"
    assert body["invoice_date"] == "2026-02-14"
    assert body["total_amount"] == "144.00"
    assert body["currency"] == "USD"
    assert body["attachment"] == {
        "filename": "figma-invoice.pdf",
        "content_type": "application/pdf",
        "url": f"/claims/{claim.id}/attachment",
    }


async def should_never_expose_the_storage_key_in_the_detail_response(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Keep the opaque storage key out of the owner-facing response body."""
    claim = await create_claim(
        test_db, owner_id=employee.id, attachment_key="super-secret-storage-key"
    )
    await test_db.commit()

    response = await client.get(f"/claims/{claim.id}", headers=employee_headers)

    assert "super-secret-storage-key" not in response.text


async def should_reject_reading_another_employees_claim(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    other_employee_headers: dict[str, str],
) -> None:
    """Return 404 so ownership is never confirmed to a non-owner."""
    claim = await create_claim(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get(f"/claims/{claim.id}", headers=other_employee_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def should_reject_unauthenticated_reads(
    client: AsyncClient, test_db: AsyncSession, employee: User
) -> None:
    """Require authentication before reading a claim."""
    claim = await create_claim(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get(f"/claims/{claim.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_stream_the_owners_attachment_content(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
    storage_backend: LocalStorageClient,
) -> None:
    """Serve the stored attachment bytes at the URL given in the detail view."""
    content = b"%PDF-1.4\nfigma invoice\n"
    claim = await create_claim(
        test_db, owner_id=employee.id, attachment_key="viewable-key"
    )
    await test_db.commit()
    await storage_backend.save(key="viewable-key", content=content)

    response = await client.get(
        f"/claims/{claim.id}/attachment", headers=employee_headers
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == content


async def should_reject_fetching_another_employees_attachment(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    other_employee_headers: dict[str, str],
    storage_backend: LocalStorageClient,
) -> None:
    """Return 404 rather than serve another employee's attachment."""
    claim = await create_claim(
        test_db, owner_id=employee.id, attachment_key="not-yours-key"
    )
    await test_db.commit()
    await storage_backend.save(key="not-yours-key", content=b"content")

    response = await client.get(
        f"/claims/{claim.id}/attachment", headers=other_employee_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def should_reject_unauthenticated_attachment_reads(
    client: AsyncClient, test_db: AsyncSession, employee: User
) -> None:
    """Require authentication before fetching a claim's attachment."""
    claim = await create_claim(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get(f"/claims/{claim.id}/attachment")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
