"""Acceptance scenarios for invoice intake."""

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient
from redis import Redis as SyncRedis
from redis.exceptions import RedisError
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_storage_client
from app.core.queue import EXTRACTION_QUEUE_NAME
from app.core.storage import StorageWriteError
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User
from app.main import app
from app.queueing import extraction

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

MAX_BYTES = 10 * 1024 * 1024
RATE_LIMIT = 20


def pdf_bytes(size: int) -> bytes:
    """Build a minimal PDF-shaped payload padded to an exact byte size."""
    header = b"%PDF-1.4\n"
    padding = b"0" * max(size - len(header), 0)
    return (header + padding)[:size]


async def should_accept_authenticated_employees_valid_pdf_as_pending_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Accept a size-compliant PDF and return its pending invoice identity."""
    response = await client.post(
        "/invoices",
        headers=employee_headers,
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


async def should_reject_oversized_body_before_authentication(
    client: AsyncClient,
) -> None:
    """Bound unauthenticated multipart bodies before dependencies and parsing."""
    response = await client.post(
        "/invoices",
        files={
            "file": (
                "huge-scan.pdf",
                pdf_bytes(MAX_BYTES + 64 * 1024),
                "application/pdf",
            )
        },
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


async def should_reject_oversized_file_without_creating_a_row(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject an oversized upload without persisting an invoice record."""
    response = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("huge-scan.pdf", pdf_bytes(MAX_BYTES + 1), "application/pdf")},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert (await test_db.scalars(select(Invoice))).first() is None


async def should_reject_disallowed_mime_type_without_creating_a_row(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject an unsupported media type without persisting an invoice record."""
    response = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("receipt.jpg", b"\xff\xd8\xff\xe0fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert (await test_db.scalars(select(Invoice))).first() is None


@pytest.mark.parametrize("content", [b"", b"MZ\x90\x00fake executable"])
async def should_reject_pdf_metadata_with_invalid_content(
    client: AsyncClient,
    test_db: AsyncSession,
    employee_headers: dict[str, str],
    content: bytes,
) -> None:
    """Require actual non-empty PDF-shaped content, not spoofable metadata."""
    response = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("invoice.pdf", content, "application/pdf")},
    )

    assert response.status_code in {
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    }
    assert (await test_db.scalars(select(Invoice))).first() is None


async def should_not_charge_invalid_uploads_against_rate_limit(
    client: AsyncClient, employee_headers: dict[str, str]
) -> None:
    """Leave the full quota available after malformed requests."""
    for _ in range(RATE_LIMIT + 1):
        rejected = await client.post(
            "/invoices",
            headers=employee_headers,
            files={"file": ("receipt.jpg", b"invalid", "image/jpeg")},
        )
        assert rejected.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    accepted = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
    )

    assert accepted.status_code == status.HTTP_201_CREATED


async def should_reject_upload_once_rate_limit_is_exhausted(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject uploads beyond the rate limit."""
    for _ in range(RATE_LIMIT):
        ok_response = await client.post(
            "/invoices",
            headers=employee_headers,
            files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
        )
        assert ok_response.status_code == status.HTTP_201_CREATED

    response = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    stored_count = len((await test_db.scalars(select(Invoice))).all())
    assert stored_count == RATE_LIMIT


async def should_return_unavailable_and_mark_row_when_storage_fails(
    client: AsyncClient,
    employee_headers: dict[str, str],
) -> None:
    """Expose a retryable response when the storage backend is unavailable."""

    class FailingStorage:
        def generate_key(self) -> str:
            return "failed-storage-key"

        async def save(self, *, key: str, content: bytes) -> None:
            raise StorageWriteError("storage unavailable")

    app.dependency_overrides[get_storage_client] = FailingStorage

    response = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


async def should_enqueue_extraction_for_every_accepted_upload(
    client: AsyncClient,
    employee_headers: dict[str, str],
    sync_redis: SyncRedis,
) -> None:
    """Push a newly-accepted invoice onto the extraction queue."""
    response = await client.post(
        "/invoices",
        headers=employee_headers,
        files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
    )

    assert response.status_code == status.HTTP_201_CREATED
    invoice_id = response.json()["invoice_id"]

    queue = Queue(EXTRACTION_QUEUE_NAME, connection=sync_redis)
    job = queue.fetch_job(extraction.get_job_id(UUID(invoice_id)))
    assert job is not None
    assert job.args == (invoice_id,)


async def should_accept_the_upload_even_when_enqueueing_fails(
    client: AsyncClient,
    test_db: AsyncSession,
    employee_headers: dict[str, str],
) -> None:
    """Mark extraction failed when broker is unavailable, but keep upload accepted."""

    with patch(
        "app.queueing.extraction.Queue.enqueue",
        side_effect=RedisError("broker unavailable"),
    ):
        response = await client.post(
            "/invoices",
            headers=employee_headers,
            files={"file": ("invoice.pdf", pdf_bytes(1024), "application/pdf")},
        )

    assert response.status_code == status.HTTP_201_CREATED
    response_body = response.json()
    assert response_body["status"] == "extraction_failed"
    invoice_id = UUID(response_body["invoice_id"])
    stored = await test_db.get(Invoice, invoice_id)
    assert stored is not None
    assert stored.status == InvoiceStatus.EXTRACTION_FAILED
