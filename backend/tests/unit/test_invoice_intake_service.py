"""Specify how invoice intake coordinates upload collaborators."""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.database.models.invoice import Invoice, InvoiceStatus
from app.services.interfaces import (
    InvoiceRepository,
    InvoiceValidator,
    RateLimiter,
    StorageClient,
)
from app.services.invoice_intake import InvoiceIntakeService

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
    validator = Mock(spec=InvoiceValidator)
    rate_limiter = AsyncMock(spec=RateLimiter)
    invoices = AsyncMock(spec=InvoiceRepository)
    storage = AsyncMock(spec=StorageClient)
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
        content=PDF_CONTENT,
    )

    assert result is stored_invoice
    context.validator.validate.assert_called_once_with(
        filename=FILENAME, content_type=CONTENT_TYPE, size=len(PDF_CONTENT)
    )
    context.rate_limiter.allow.assert_awaited_once_with(OWNER_ID)
    context.storage.generate_key.assert_called_once_with()
    context.invoices.create_pending.assert_awaited_once_with(
        owner_id=OWNER_ID, storage_key=STORAGE_KEY, original_filename=FILENAME
    )
    context.storage.save.assert_awaited_once_with(key=STORAGE_KEY, content=PDF_CONTENT)
