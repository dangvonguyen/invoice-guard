"""Behavior specifications for invoice upload validation."""

import pytest

from app.services.invoice_mime_validator import (
    InvoiceMimeValidator,
    PayloadTooLargeError,
    UnreadableUploadError,
    UnsupportedMediaTypeError,
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
        filename="invoice.pdf",
        content_type="application/pdf",
        size=CAP_BYTES,
        content=b"%PDF-" + b"0" * (CAP_BYTES - 5),
    )


def should_reject_a_file_at_exactly_cap_plus_one_byte(
    validator: InvoiceMimeValidator,
) -> None:
    """Reject a file exactly one byte over the cap (boundary)."""
    with pytest.raises(PayloadTooLargeError):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            size=CAP_BYTES + 1,
            content=b"%PDF-",
        )


def should_reject_when_size_cannot_be_determined(
    validator: InvoiceMimeValidator,
) -> None:
    """Reject rather than silently accept an unknown/unreported size."""
    with pytest.raises(UnreadableUploadError):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            size=None,
            content=b"%PDF-",
        )


def should_reject_image_with_a_not_yet_supported_reason(
    validator: InvoiceMimeValidator,
) -> None:
    """Reject a disallowed MIME type, naming PDF as the current format."""
    with pytest.raises(UnsupportedMediaTypeError, match="PDF"):
        validator.validate(
            filename="receipt.jpg", content_type="image/jpeg", size=100, content=b"x"
        )


def should_reject_extension_that_disagrees_with_declared_content_type(
    validator: InvoiceMimeValidator,
) -> None:
    """Reject when the filename extension doesn't match the declared type.

    The Content-Type header is client-supplied and spoofable; trusting it
    alone would let a mislabeled file pass.
    """
    with pytest.raises(UnsupportedMediaTypeError):
        validator.validate(
            filename="invoice.jpg",
            content_type="application/pdf",
            size=100,
            content=b"%PDF-",
        )


def should_reject_empty_pdf(validator: InvoiceMimeValidator) -> None:
    """Reject empty content even when its metadata claims it is a PDF."""
    with pytest.raises(UnreadableUploadError, match="empty"):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            size=0,
            content=b"",
        )


def should_reject_spoofed_pdf_content(validator: InvoiceMimeValidator) -> None:
    """Reject arbitrary bytes carrying PDF metadata."""
    with pytest.raises(UnsupportedMediaTypeError, match="not a PDF"):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            size=8,
            content=b"MZ\x90\x00fake",
        )
