"""Specify how the extraction job handles transient provider failures."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.core.storage import StorageClient
from app.services.interfaces import (
    ExtractionService,
    InvoiceRepository,
    PdfTextExtractor,
)
from app.workers.extract_invoice import InvoiceNotFoundError, extract_invoice

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

INVOICE_ID = UUID("10000000-0000-0000-0000-000000000001")
STORAGE_KEY = "20000000-0000-0000-0000-000000000001"
PDF_CONTENT = b"%PDF-1.4\ninvoice content\n"
DOCUMENT_TEXT = "Vendor: Acme Supplies\nTotal: 482.10 USD"
EXTRACTION_RESULT = {
    "vendor_name": "Acme Supplies",
    "invoice_number": "INV-2026-00142",
    "invoice_date": "2026-08-03",
    "currency": "USD",
    "subtotal": "450.00",
    "tax_amount": "32.10",
    "total_amount": "482.10",
    "line_items": [],
}


@dataclass(frozen=True)
class ExtractionWorkerContext:
    """Expose the worker and collaborator roles used by each scenario."""

    invoices: AsyncMock
    storage: AsyncMock
    text_extractor: Mock
    extraction_service: AsyncMock

    async def run(self) -> None:
        """Run the worker with its external boundaries replaced."""
        await extract_invoice(
            INVOICE_ID,
            invoices=self.invoices,
            storage=self.storage,
            text_extractor=self.text_extractor,
            extraction_service=self.extraction_service,
        )


@pytest.fixture
def context() -> ExtractionWorkerContext:
    """Build an extraction job context with mocked external boundaries."""
    invoices = AsyncMock(spec=InvoiceRepository)
    invoice = Mock(storage_key=STORAGE_KEY)
    invoices.get_by_id.return_value = invoice

    storage = AsyncMock(spec=StorageClient)
    storage.read.return_value = PDF_CONTENT

    text_extractor = Mock(spec=PdfTextExtractor)
    text_extractor.extract_text.return_value = DOCUMENT_TEXT

    return ExtractionWorkerContext(
        invoices=invoices,
        storage=storage,
        text_extractor=text_extractor,
        extraction_service=AsyncMock(spec=ExtractionService),
    )


async def should_persist_extracted_fields_on_first_successful_attempt(
    context: ExtractionWorkerContext,
) -> None:
    """Read, extract, and persist a valid invoice without retrying."""
    context.extraction_service.extract.return_value = EXTRACTION_RESULT

    await context.run()

    context.invoices.get_by_id.assert_awaited_once_with(INVOICE_ID)
    context.storage.read.assert_awaited_once_with(key=STORAGE_KEY)
    context.text_extractor.extract_text.assert_called_once_with(content=PDF_CONTENT)
    context.extraction_service.extract.assert_awaited_once_with(
        document_text=DOCUMENT_TEXT
    )
    context.invoices.mark_extracted.assert_awaited_once_with(
        invoice_id=INVOICE_ID,
        extraction_result=EXTRACTION_RESULT,
    )


async def should_reject_an_unknown_invoice_before_reading_storage(
    context: ExtractionWorkerContext,
) -> None:
    """Fail clearly when a queued invoice no longer exists."""
    context.invoices.get_by_id.return_value = None

    with pytest.raises(InvoiceNotFoundError, match=str(INVOICE_ID)):
        await context.run()

    context.storage.read.assert_not_awaited()
    context.extraction_service.extract.assert_not_awaited()
    context.invoices.mark_extracted.assert_not_awaited()
