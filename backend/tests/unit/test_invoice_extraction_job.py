"""Specify how the extraction job handles transient provider failures."""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.database.models.invoice import Invoice, InvoiceStatus
from app.services.extraction_model import InvoiceFields
from app.services.extraction_service import ExtractionResult
from app.workers.extract_invoice import InvoiceNotFoundError, extract_invoice

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
INVOICE_ID = UUID("10000000-0000-0000-0000-000000000001")
STORAGE_KEY = "20000000-0000-0000-0000-000000000001"
PDF_CONTENT = b"%PDF-1.4\ninvoice content\n"
DOCUMENT_TEXT = "Vendor: Acme Supplies\nTotal: 482.10 USD"
EXTRACTED_FIELDS = {
    "vendor_name": "Acme Supplies",
    "invoice_date": "2000-01-01",
    "currency": "USD",
    "tax_amount": "32.10",
    "total_amount": "482.10",
    "line_items": [],
}


@dataclass(frozen=True)
class JobContext:
    """Expose the job and collaborator roles used by each scenario."""

    invoices: AsyncMock
    storage: AsyncMock
    text_extractor: Mock
    extraction_service: AsyncMock

    async def run(self) -> None:
        """Run the job with its external boundaries replaced."""
        await extract_invoice(
            INVOICE_ID,
            invoices=self.invoices,
            storage=self.storage,
            text_extractor=self.text_extractor,
            extraction_service=self.extraction_service,
        )


@pytest.fixture
def stored_invoice() -> Invoice:
    timestamp = datetime(2000, 1, 1, tzinfo=UTC)
    return Invoice(
        id=INVOICE_ID,
        owner_id=OWNER_ID,
        status=InvoiceStatus.PENDING,
        storage_key=STORAGE_KEY,
        original_filename="invoice.pdf",
        created_at=timestamp,
    )


@pytest.fixture
def extraction_result() -> ExtractionResult:
    fields = InvoiceFields.model_validate(EXTRACTED_FIELDS)
    return ExtractionResult(fields=fields, confidence="high", confidence_reason=None)


@pytest.fixture
def context(stored_invoice: Invoice, extraction_result: ExtractionResult) -> JobContext:
    """Build an extraction job context with mocked external boundaries."""
    invoices = AsyncMock()
    invoices.get_by_id.return_value = stored_invoice
    storage = AsyncMock()
    storage.read.return_value = PDF_CONTENT
    text_extractor = Mock()
    text_extractor.extract_text.return_value = DOCUMENT_TEXT
    extraction_service = AsyncMock()
    extraction_service.extract.return_value = extraction_result
    return JobContext(
        invoices=invoices,
        storage=storage,
        text_extractor=text_extractor,
        extraction_service=extraction_service,
    )


async def should_persist_extracted_fields_on_first_successful_attempt(
    context: JobContext, extraction_result: ExtractionResult
) -> None:
    """Read, extract, and persist a valid invoice without retrying."""
    await context.run()

    context.invoices.get_by_id.assert_awaited_once_with(INVOICE_ID)
    context.storage.read.assert_awaited_once_with(key=STORAGE_KEY)
    context.text_extractor.extract_text.assert_called_once_with(content=PDF_CONTENT)
    context.extraction_service.extract.assert_awaited_once_with(
        document_text=DOCUMENT_TEXT
    )
    context.invoices.mark_extracted.assert_awaited_once_with(
        invoice_id=INVOICE_ID,
        fields=extraction_result.fields.model_dump(mode="json"),
        confidence=extraction_result.confidence,
        confidence_reason=extraction_result.confidence_reason,
    )


async def should_reject_an_unknown_invoice_before_reading_storage(
    context: JobContext,
) -> None:
    """Fail clearly when a queued invoice no longer exists."""
    context.invoices.get_by_id.return_value = None

    with pytest.raises(InvoiceNotFoundError, match=str(INVOICE_ID)):
        await context.run()

    context.storage.read.assert_not_awaited()
    context.extraction_service.extract.assert_not_awaited()
    context.invoices.mark_extracted.assert_not_awaited()
