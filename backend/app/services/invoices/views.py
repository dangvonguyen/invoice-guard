"""Map a persisted invoice into its role-specific API response shape."""

from app.database.models.invoice import ExtractionConfidence, Invoice
from app.schemas.invoice import InvoiceDetailResponse, InvoiceSummary


def employee_view(invoice: Invoice) -> InvoiceDetailResponse:
    """Build the employee-facing detail view for an owned invoice."""
    # If extraction confidence is high, show data summary
    invoice_summary: InvoiceSummary | None = None
    if (
        invoice.confidence == ExtractionConfidence.HIGH
        and invoice.extracted_fields is not None
    ):
        invoice_summary = InvoiceSummary.model_validate(invoice.extracted_fields)

    return InvoiceDetailResponse(
        id=invoice.id,
        status=invoice.status,
        invoice_summary=invoice_summary,
    )
