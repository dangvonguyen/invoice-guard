"""Acceptance scenarios for invoice intake."""

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient, Response
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
from app.queueing import invoice_processing

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

MAX_BYTES = 10 * 1024 * 1024
RATE_LIMIT = 20


def padded_pdf_bytes(size: int) -> bytes:
    """Build a minimal PDF-shaped payload padded to an exact byte size."""
    header = b"%PDF-1.4\n"
    padding = b"0" * max(size - len(header), 0)
    return (header + padding)[:size]


async def upload(
    client: AsyncClient,
    *,
    headers: dict[str, str] | None = None,
    filename: str = "invoice.pdf",
    content: bytes | None = None,
    size: int = 1024,
    content_type: str = "application/pdf",
) -> Response:
    """POST a multipart invoice upload, defaulting to a valid, size-compliant PDF."""
    body = content if content is not None else padded_pdf_bytes(size)
    return await client.post(
        "/invoices",
        headers=headers,
        files={"file": (filename, body, content_type)},
    )


async def should_accept_authenticated_employees_valid_pdf_as_processing_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Accept a size-compliant PDF and return its processing invoice identity."""
    response = await upload(client, headers=employee_headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "processing"
    invoice_id = UUID(body["data"]["id"])

    stored = await test_db.get(Invoice, invoice_id)
    assert stored is not None
    assert stored.owner_id == employee.id
    assert stored.status == InvoiceStatus.PROCESSING
    assert stored.storage_key


async def should_reject_unauthenticated_upload(client: AsyncClient) -> None:
    """Require authentication before accepting an invoice upload."""
    response = await upload(client)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_oversized_body_before_authentication(
    client: AsyncClient,
) -> None:
    """Bound unauthenticated multipart bodies before dependencies and parsing."""
    response = await upload(
        client, filename="huge-scan.pdf", size=MAX_BYTES + 64 * 1024
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


async def should_reject_oversized_file_without_creating_a_row(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject an oversized upload without persisting an invoice record."""
    response = await upload(
        client,
        headers=employee_headers,
        filename="huge-scan.pdf",
        size=MAX_BYTES + 1,
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert (await test_db.scalars(select(Invoice))).first() is None


async def should_reject_disallowed_mime_type_without_creating_a_row(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject an unsupported media type without persisting an invoice record."""
    response = await upload(
        client,
        headers=employee_headers,
        filename="receipt.jpg",
        content=b"\xff\xd8\xff\xe0fake-jpeg",
        content_type="image/jpeg",
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
    response = await upload(client, headers=employee_headers, content=content)

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
        rejected = await upload(
            client,
            headers=employee_headers,
            filename="receipt.jpg",
            content=b"invalid",
            content_type="image/jpeg",
        )
        assert rejected.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    accepted = await upload(client, headers=employee_headers)

    assert accepted.status_code == status.HTTP_201_CREATED


async def should_reject_upload_once_rate_limit_is_exhausted(
    client: AsyncClient, test_db: AsyncSession, employee_headers: dict[str, str]
) -> None:
    """Reject uploads beyond the rate limit."""
    for _ in range(RATE_LIMIT):
        ok_response = await upload(client, headers=employee_headers)
        assert ok_response.status_code == status.HTTP_201_CREATED

    response = await upload(client, headers=employee_headers)

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

    response = await upload(client, headers=employee_headers)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


async def should_enqueue_extraction_for_every_accepted_upload(
    client: AsyncClient,
    employee_headers: dict[str, str],
    sync_redis: SyncRedis,
) -> None:
    """Push a newly-accepted invoice onto the extraction queue."""
    response = await upload(client, headers=employee_headers)

    assert response.status_code == status.HTTP_201_CREATED
    invoice_id = response.json()["data"]["id"]

    queue = Queue(EXTRACTION_QUEUE_NAME, connection=sync_redis)
    job = queue.fetch_job(invoice_processing.get_job_id(UUID(invoice_id)))
    assert job is not None
    assert job.args == (invoice_id,)


async def should_accept_the_upload_even_when_enqueueing_fails(
    client: AsyncClient,
    test_db: AsyncSession,
    employee_headers: dict[str, str],
) -> None:
    """Mark extraction failed when broker is unavailable, but keep upload accepted."""

    with patch(
        "app.queueing.invoice_processing.Queue.enqueue",
        side_effect=RedisError("broker unavailable"),
    ):
        response = await upload(client, headers=employee_headers)

    assert response.status_code == status.HTTP_201_CREATED
    response_body = response.json()["data"]
    assert response_body["status"] == "processing_error"
    invoice_id = UUID(response_body["id"])
    stored = await test_db.get(Invoice, invoice_id)
    assert stored is not None
    assert stored.status == InvoiceStatus.PROCESSING_ERROR
