"""Map a persisted invoice into its role-specific API response shape."""

from app.database.models.invoice import ExtractionConfidence, Invoice
from app.schemas.invoice import InvoiceDetailResponse, InvoiceSummary


def build_invoice_summary(invoice: Invoice) -> InvoiceSummary | None:
    """Condense an invoice's extracted fields, or omit them if untrustworthy."""
    if (
        invoice.confidence != ExtractionConfidence.HIGH
        or invoice.extracted_fields is None
    ):
        return None
    return InvoiceSummary.model_validate(invoice.extracted_fields)


def employee_view(invoice: Invoice) -> InvoiceDetailResponse:
    """Build the employee-facing detail view for an owned invoice."""
    return InvoiceDetailResponse(
        id=invoice.id,
        status=invoice.status,
        invoice_summary=build_invoice_summary(invoice),
    )
