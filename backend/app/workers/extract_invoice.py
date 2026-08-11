"""Worker entry point for extracting structured fields from stored invoices."""

from uuid import UUID

from app.core.storage import StorageClient
from app.services.interfaces import (
    ExtractionService,
    InvoiceRepository,
    PdfTextExtractor,
)


class InvoiceNotFoundError(Exception):
    """Raised when an extraction job references an unknown invoice."""


async def extract_invoice(
    invoice_id: UUID,
    *,
    invoices: InvoiceRepository,
    storage: StorageClient,
    text_extractor: PdfTextExtractor,
    extraction_service: ExtractionService,
) -> None:
    """Extract and persist structured fields for one stored invoice."""
    invoice = await invoices.get_by_id(invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError(f"invoice {invoice_id} does not exist")

    pdf_content = await storage.read(key=invoice.storage_key)
    document_text = text_extractor.extract_text(content=pdf_content)
    result = await extraction_service.extract(document_text=document_text)

    await invoices.mark_extracted(invoice_id=invoice_id, extraction_result=result)
