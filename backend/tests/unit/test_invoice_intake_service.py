"""Specify how invoice intake coordinates upload collaborators."""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.core.storage import StorageWriteError
from app.database.models.invoice import Invoice, InvoiceStatus
from app.services.invoice_intake import (
    InvoiceIntakeService,
    InvoiceStorageUnavailableError,
    UploadRateLimitExceededError,
)
from app.services.invoice_mime_validator import UnsupportedMediaTypeError

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
INVOICE_ID = UUID("10000000-0000-0000-0000-000000000001")
STORAGE_KEY = UUID("20000000-0000-0000-0000-000000000001")
FILENAME = "invoice.pdf"
CONTENT_TYPE = "application/pdf"
PDF_CONTENT = b"%PDF-1.4\ninvoice content\n"


@dataclass(frozen=True)
class IntakeContext:
    """Expose the service and collaborator roles used by the scenario."""

    service: InvoiceIntakeService
    validator: Mock
    rate_limiter: AsyncMock
    invoices: AsyncMock
    storage: AsyncMock


@pytest.fixture
def stored_invoice() -> Invoice:
    """Return the invoice the repository hands back on a successful create."""
    timestamp = datetime(2000, 1, 1, tzinfo=UTC)
    return Invoice(
        id=INVOICE_ID,
        owner_id=OWNER_ID,
        status=InvoiceStatus.PENDING,
        storage_key=STORAGE_KEY,
        original_filename=FILENAME,
        created_at=timestamp,
    )


@pytest.fixture
def context() -> IntakeContext:
    """Build invoice intake with mocks for the roles it coordinates."""
    validator = Mock()
    rate_limiter = AsyncMock()
    invoices = AsyncMock()
    storage = AsyncMock()
    service = InvoiceIntakeService(
        validator=validator,
        rate_limiter=rate_limiter,
        invoices=invoices,
        storage=storage,
    )
    return IntakeContext(
        service=service,
        validator=validator,
        rate_limiter=rate_limiter,
        invoices=invoices,
        storage=storage,
    )


async def should_accept_valid_pdf_as_pending_invoice(
    context: IntakeContext, stored_invoice: Invoice
) -> None:
    """Validate, reserve, and store an authenticated employee's PDF."""
    context.rate_limiter.allow.return_value = True
    context.storage.generate_key.return_value = STORAGE_KEY
    context.invoices.create_pending.return_value = stored_invoice

    result = await context.service.upload(
        owner_id=OWNER_ID,
        filename=FILENAME,
        content_type=CONTENT_TYPE,
        size=len(PDF_CONTENT),
        content=PDF_CONTENT,
    )

    assert result is stored_invoice
    context.validator.validate.assert_called_once_with(
        filename=FILENAME,
        content_type=CONTENT_TYPE,
        size=len(PDF_CONTENT),
        content=PDF_CONTENT,
    )
    context.rate_limiter.allow.assert_awaited_once_with(
        key=OWNER_ID, scope="invoice-upload"
    )
    context.storage.generate_key.assert_called_once_with()
    context.invoices.create_pending.assert_awaited_once_with(
        owner_id=OWNER_ID, storage_key=STORAGE_KEY, original_filename=FILENAME
    )
    context.storage.save.assert_awaited_once_with(key=STORAGE_KEY, content=PDF_CONTENT)


async def should_write_storage_only_after_the_row_is_created(
    context: IntakeContext,
) -> None:
    """Never attempt a storage write before the row is durably persisted."""
    call_order: list[str] = []
    context.rate_limiter.allow.return_value = True
    context.invoices.create_pending.side_effect = lambda **_: call_order.append(
        "create_pending"
    )
    context.storage.save.side_effect = lambda **_: call_order.append("save")

    await context.service.upload(
        owner_id=OWNER_ID,
        filename=FILENAME,
        content_type=CONTENT_TYPE,
        size=len(PDF_CONTENT),
        content=PDF_CONTENT,
    )

    assert call_order == ["create_pending", "save"]


async def should_reject_upload_when_rate_limit_denies_it(
    context: IntakeContext,
) -> None:
    """Validate, then reject before touching persistence or storage."""
    context.rate_limiter.allow.return_value = False

    with pytest.raises(UploadRateLimitExceededError):
        await context.service.upload(
            owner_id=OWNER_ID,
            filename=FILENAME,
            content_type=CONTENT_TYPE,
            size=len(PDF_CONTENT),
            content=PDF_CONTENT,
        )

    context.validator.validate.assert_called_once()
    context.invoices.create_pending.assert_not_awaited()
    context.storage.save.assert_not_awaited()


async def should_reject_upload_when_validation_fails_without_persisting(
    context: IntakeContext,
) -> None:
    """Propagate validation errors and never create a row or write storage."""
    context.validator.validate.side_effect = UnsupportedMediaTypeError()

    with pytest.raises(UnsupportedMediaTypeError):
        await context.service.upload(
            owner_id=OWNER_ID,
            filename="receipt.jpg",
            content_type="image/jpeg",
            size=10,
            content=b"x",
        )

    context.invoices.create_pending.assert_not_awaited()
    context.storage.save.assert_not_awaited()
    context.rate_limiter.allow.assert_not_awaited()


async def should_generate_a_storage_key_never_derived_from_the_filename(
    context: IntakeContext,
) -> None:
    """Never pass the client-supplied filename through as the storage key."""
    context.rate_limiter.allow.return_value = True
    await context.service.upload(
        owner_id=OWNER_ID,
        filename="invoice.pdf",
        content_type=CONTENT_TYPE,
        size=len(PDF_CONTENT),
        content=PDF_CONTENT,
    )

    _, kwargs = context.invoices.create_pending.await_args
    assert kwargs["storage_key"] != "invoice.pdf"
    assert kwargs["original_filename"] == "invoice.pdf"


async def should_mark_reservation_failed_when_storage_write_fails(
    context: IntakeContext, stored_invoice: Invoice
) -> None:
    """Translate storage failure and durably mark the reserved row failed."""
    context.rate_limiter.allow.return_value = True
    context.storage.generate_key.return_value = STORAGE_KEY
    context.invoices.create_pending.return_value = stored_invoice
    context.storage.save.side_effect = StorageWriteError("disk unavailable")

    with pytest.raises(InvoiceStorageUnavailableError):
        await context.service.upload(
            owner_id=OWNER_ID,
            filename=FILENAME,
            content_type=CONTENT_TYPE,
            size=len(PDF_CONTENT),
            content=PDF_CONTENT,
        )

    context.invoices.mark_upload_failed.assert_awaited_once_with(invoice_id=INVOICE_ID)
