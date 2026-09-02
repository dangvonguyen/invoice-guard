"""Acceptance scenarios for claim submission."""

import json
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorageClient
from app.database.models.claim import Claim, ClaimEntryMethod, ClaimStatus
from app.database.models.user import User
from tests.support.constants import VALID_SUBMISSION_PAYLOAD

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

PDF_CONTENT = b"%PDF-1.4\nfigma invoice\n"


def valid_submission_data(**overrides: object) -> dict[str, object]:
    """A complete, valid claim-submission ``data`` payload."""
    data = VALID_SUBMISSION_PAYLOAD.copy()
    data.update(overrides)
    return data


async def submit_claim(
    client: AsyncClient,
    *,
    headers: dict[str, str] | None = None,
    data_overrides: dict[str, object] | None = None,
    filename: str = "figma-invoice.pdf",
    content: bytes | None = None,
    content_type: str = "application/pdf",
) -> Response:
    """POST a multipart claim submission, defaulting to a valid PDF + payload."""
    data = valid_submission_data(**(data_overrides or {}))
    body = content if content is not None else PDF_CONTENT
    return await client.post(
        "/claims",
        headers=headers,
        data={"data": json.dumps(data)},
        files={"file": (filename, body, content_type)},
    )


async def should_land_a_certified_manual_submission_in_submitted(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
    storage_backend: LocalStorageClient,
) -> None:
    """Accept a one-call manual submission and persist it as a submitted claim."""
    response = await submit_claim(client, headers=employee_headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "submitted"

    claim_id = UUID(body["data"]["id"])
    stored = await test_db.get(Claim, claim_id)

    assert stored is not None

    # Submission state
    assert stored.owner_id == employee.id
    assert stored.status == ClaimStatus.SUBMITTED
    assert stored.entry_method == ClaimEntryMethod.MANUAL
    assert stored.certified_at is not None

    # Claim data
    assert stored.expense_title == "Annual Figma subscription"
    assert stored.business_purpose.startswith("Design tooling")
    assert stored.category.value == "software_hosting"
    assert stored.cost_center == "PRODUCT-DESIGN"
    assert stored.vendor == "Figma Inc."
    assert stored.invoice_number == "FIG-2026-00417"
    assert stored.invoice_date == date(2026, 2, 14)
    assert stored.total_amount == Decimal("144.00")
    assert stored.tax_amount == Decimal("0.00")
    assert stored.currency == "USD"

    # Attachment
    assert stored.attachment_filename == "figma-invoice.pdf"
    assert stored.attachment_content_type == "application/pdf"
    assert stored.attachment_bytes == len(PDF_CONTENT)
    assert await storage_backend.read(key=stored.attachment_key) == PDF_CONTENT
