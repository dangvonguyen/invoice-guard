"""Behavior specifications for invoice upload validation."""

import pytest

from app.services.invoice_mime_validator import InvoiceMimeValidator

pytestmark = pytest.mark.unit

CAP_BYTES = 1024


def should_accept_pdf_with_supported_metadata_and_size() -> None:
    """Accept a correctly-typed PDF within the size cap."""
    validator = InvoiceMimeValidator()

    validator.validate(
        filename="acme-invoice.pdf",
        content_type="application/pdf",
        size=CAP_BYTES,
    )
