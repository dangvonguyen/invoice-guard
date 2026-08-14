"""Worker entry point for extracting structured fields from stored invoices."""

from uuid import UUID

from app.core.storage import StorageClient
from app.database.repositories.invoice import InvoiceRepository
from app.services.extraction.pipeline import ExtractionPipeline, InvalidModelOutputError
from app.services.extraction.text import NoTextLayerError, TextExtractor


class InvoiceNotFoundError(Exception):
    """Raised when an extraction job references an unknown invoice."""


async def extract_invoice(
    invoice_id: UUID,
    *,
    invoices: InvoiceRepository,
    storage: StorageClient,
    text_extractor: TextExtractor,
    extraction_pipeline: ExtractionPipeline,
) -> None:
    """Extract and persist structured fields for one stored invoice."""
    invoice = await invoices.get_by_id(invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError(f"invoice {invoice_id} does not exist")

    pdf_content = await storage.read(key=invoice.storage_key)
    try:
        document_text = text_extractor.extract_text(content=pdf_content)
    except NoTextLayerError:
        await invoices.mark_extraction_failed(invoice_id=invoice_id)
        return

    try:
        result = await extraction_pipeline.run(document_text=document_text)
    except InvalidModelOutputError:
        await invoices.mark_extraction_failed(invoice_id=invoice_id)
        return

    await invoices.mark_extracted(
        invoice_id=invoice_id,
        fields=result.fields.model_dump(mode="json"),
        confidence=result.confidence,
        confidence_reason=result.confidence_reason,
    )
