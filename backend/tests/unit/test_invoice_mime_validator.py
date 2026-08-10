"""Behavior specifications for invoice upload validation."""

import pytest

from app.services.invoice_mime_validator import (
    InvoiceMimeValidator,
    PayloadTooLargeError,
    UnreadableUploadError,
)

pytestmark = pytest.mark.unit

CAP_BYTES = 1024


@pytest.fixture
def validator() -> InvoiceMimeValidator:
    """Provide a validator with a small cap so tests stay fast and exact."""
    return InvoiceMimeValidator(max_bytes=CAP_BYTES)


def should_accept_pdf_with_supported_metadata_and_size(
    validator: InvoiceMimeValidator,
) -> None:
    """Accept a correctly-typed PDF within the size cap."""
    validator.validate(
        filename="invoice.pdf", content_type="application/pdf", size=CAP_BYTES
    )


def should_reject_a_file_at_exactly_cap_plus_one_byte(
    validator: InvoiceMimeValidator,
) -> None:
    """Reject a file exactly one byte over the cap (boundary)."""
    with pytest.raises(PayloadTooLargeError):
        validator.validate(
            filename="invoice.pdf", content_type="application/pdf", size=CAP_BYTES + 1
        )


def should_reject_when_size_cannot_be_determined(
    validator: InvoiceMimeValidator,
) -> None:
    """Reject rather than silently accept an unknown/unreported size."""
    with pytest.raises(UnreadableUploadError):
        validator.validate(
            filename="invoice.pdf", content_type="application/pdf", size=None
        )
