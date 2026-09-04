"""Acceptance scenarios for claim submission."""

import json
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_storage_client
from app.core.storage import LocalStorageClient, StorageWriteError
from app.database.models.claim import Claim, ClaimStatus
from app.database.models.user import User
from app.main import app
from tests.support.constants import VALID_SUBMISSION_PAYLOAD

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

PDF_CONTENT = b"%PDF-1.4\nfigma invoice\n"
JPEG_CONTENT = b"\xff\xd8\xff\xe0fake-jpeg-body"
PNG_CONTENT = b"\x89PNG\r\n\x1a\nfake-png-body"
MAX_BYTES = 10 * 1024 * 1024
RATE_LIMIT = 20


def padded_pdf(size: int) -> bytes:
    """A PDF-shaped payload padded to an exact byte length."""
    header = b"%PDF-1.4\n"
    return (header + b"0" * max(size - len(header), 0))[:size]


async def count_claims(test_db: AsyncSession) -> int:
    """Total claim rows currently visible to the test session."""
    return await test_db.scalar(select(func.count()).select_from(Claim)) or 0


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
    """Accept a one-call submission and persist it as a submitted claim."""
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
    assert stored.original_total_amount == Decimal("144.00")
    assert stored.currency == "USD"

    # Attachment
    assert stored.attachment_filename == "figma-invoice.pdf"
    assert stored.attachment_content_type == "application/pdf"
    assert stored.attachment_bytes == len(PDF_CONTENT)
    assert await storage_backend.read(key=stored.attachment_key) == PDF_CONTENT


async def should_reject_an_unauthenticated_submission(
    client: AsyncClient, test_db: AsyncSession
) -> None:
    """Require authentication before accepting a claim submission."""
    response = await submit_claim(client)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert await count_claims(test_db) == 0


async def should_reject_a_submission_that_is_not_certified(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Refuse to create a claim unless the certification flag is set."""
    response = await submit_claim(
        client, headers=employee_headers, data_overrides={"certified": False}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert await count_claims(test_db) == 0


@pytest.mark.parametrize(
    "bad_field",
    [
        {"vendor": ""},
        {"total_amount": "0"},
        {"invoice_date": ""},
        {"currency": ""},
    ],
)
async def should_reject_a_submission_missing_required_invoice_facts(
    client: AsyncClient,
    test_db: AsyncSession,
    employee_headers: dict[str, str],
    bad_field: dict[str, object],
) -> None:
    """Block submission when a required invoice fact is blank or invalid."""
    response = await submit_claim(
        client, headers=employee_headers, data_overrides=bad_field
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert await count_claims(test_db) == 0


async def should_reject_an_unknown_category(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Only accept categories from the fixed list."""
    response = await submit_claim(
        client, headers=employee_headers, data_overrides={"category": "rocket_fuel"}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert await count_claims(test_db) == 0


async def should_accept_a_jpeg_photo_of_a_paper_receipt(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Accept a JPEG attachment on equal footing with a PDF."""
    response = await submit_claim(
        client,
        headers=employee_headers,
        filename="receipt.jpg",
        content=JPEG_CONTENT,
        content_type="image/jpeg",
    )

    assert response.status_code == status.HTTP_201_CREATED
    claim_id = UUID(response.json()["data"]["id"])
    stored = await test_db.get(Claim, claim_id)
    assert stored is not None
    assert stored.attachment_content_type == "image/jpeg"


async def should_accept_a_png_photo_of_a_paper_receipt(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Accept a PNG attachment on equal footing with a PDF."""
    response = await submit_claim(
        client,
        headers=employee_headers,
        filename="receipt.png",
        content=PNG_CONTENT,
        content_type="image/png",
    )

    assert response.status_code == status.HTTP_201_CREATED
    claim_id = UUID(response.json()["data"]["id"])
    stored = await test_db.get(Claim, claim_id)
    assert stored is not None
    assert stored.attachment_content_type == "image/png"


async def should_reject_an_unsupported_attachment_type(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject an attachment type outside PDF/JPEG/PNG without persisting a claim."""
    response = await submit_claim(
        client,
        headers=employee_headers,
        filename="receipt.gif",
        content=b"GIF89afake-gif-body",
        content_type="image/gif",
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert await count_claims(test_db) == 0


async def should_reject_an_oversized_attachment(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject an attachment over the size cap without persisting a claim."""
    response = await submit_claim(
        client,
        headers=employee_headers,
        filename="huge-scan.pdf",
        content=padded_pdf(MAX_BYTES + 1),
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert await count_claims(test_db) == 0


async def should_reject_an_oversized_image_attachment(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Apply the same size cap to image attachments as to PDFs."""
    header = b"\xff\xd8\xff\xe0"
    oversized = (header + b"0" * (MAX_BYTES + 1 - len(header)))[: MAX_BYTES + 1]
    response = await submit_claim(
        client,
        headers=employee_headers,
        filename="huge-scan.jpg",
        content=oversized,
        content_type="image/jpeg",
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert await count_claims(test_db) == 0


async def should_reject_an_oversized_body_before_authentication(
    client: AsyncClient,
) -> None:
    """Bound the multipart body before dependencies or parsing run."""
    response = await submit_claim(
        client, filename="huge-scan.pdf", content=padded_pdf(MAX_BYTES + 128 * 1024)
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


async def should_return_unavailable_when_attachment_storage_fails(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Expose a retryable 503 and leave no claim when storage is down."""

    class FailingStorage:
        def generate_key(self) -> str:
            return "failed-claim-key"

        async def save(self, *, key: str, content: bytes) -> None:
            raise StorageWriteError("storage unavailable")

    app.dependency_overrides[get_storage_client] = FailingStorage
    try:
        response = await submit_claim(client, headers=employee_headers)
    finally:
        app.dependency_overrides.pop(get_storage_client, None)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert await count_claims(test_db) == 0


async def should_not_charge_invalid_submissions_against_the_rate_limit(
    client: AsyncClient, employee_headers: dict[str, str]
) -> None:
    """Leave the full quota available after malformed submissions."""
    for _ in range(RATE_LIMIT + 1):
        rejected = await submit_claim(
            client,
            headers=employee_headers,
            filename="receipt.jpg",
            content=b"not-a-pdf",
            content_type="image/jpeg",
        )
        assert rejected.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    accepted = await submit_claim(client, headers=employee_headers)

    assert accepted.status_code == status.HTTP_201_CREATED


async def should_reject_submissions_once_the_rate_limit_is_exhausted(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject submissions beyond the per-employee rate limit."""
    for _ in range(RATE_LIMIT):
        ok = await submit_claim(client, headers=employee_headers)
        assert ok.status_code == status.HTTP_201_CREATED

    response = await submit_claim(client, headers=employee_headers)

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert await count_claims(test_db) == RATE_LIMIT
