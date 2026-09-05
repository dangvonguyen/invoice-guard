"""Behavior specifications for invoice upload validation."""

import pytest

from app.services.upload.validation import (
    DOCUMENT_ALLOWED_MEDIA_TYPES,
    InvalidFilenameError,
    InvalidPayloadError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    UploadValidator,
)

pytestmark = pytest.mark.unit

CAP_BYTES = 1024


@pytest.fixture
def validator() -> UploadValidator:
    """Provide a validator with a small cap so tests stay fast and exact."""
    return UploadValidator(max_bytes=CAP_BYTES)


def should_accept_pdf_with_supported_metadata_and_size(
    validator: UploadValidator,
) -> None:
    """Accept a correctly-typed PDF within the size cap."""
    validator.validate(
        filename="invoice.pdf",
        content_type="application/pdf",
        content_length=CAP_BYTES,
        content=b"%PDF-" + b"0" * (CAP_BYTES - 5),
    )


def should_reject_a_file_at_exactly_cap_plus_one_byte(
    validator: UploadValidator,
) -> None:
    """Reject a file exactly one byte over the cap (boundary)."""
    with pytest.raises(PayloadTooLargeError):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            content_length=CAP_BYTES + 1,
            content=b"%PDF-" + b"0" * (CAP_BYTES - 4),
        )


def should_reject_when_size_cannot_be_determined(
    validator: UploadValidator,
) -> None:
    """Reject rather than silently accept an unknown/unreported size."""
    with pytest.raises(InvalidPayloadError):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            content_length=None,
            content=b"%PDF-",
        )


def should_reject_image_with_a_not_yet_supported_reason(
    validator: UploadValidator,
) -> None:
    """Reject a disallowed MIME type, naming PDF as the current format."""
    with pytest.raises(UnsupportedMediaTypeError, match="PDF"):
        validator.validate(
            filename="receipt.jpg",
            content_type="image/jpeg",
            content_length=100,
            content=b"x",
        )


def should_reject_extension_that_disagrees_with_declared_content_type(
    validator: UploadValidator,
) -> None:
    """Reject when the filename extension doesn't match the declared type.

    The Content-Type header is client-supplied and spoofable; trusting it
    alone would let a mislabeled file pass.
    """
    with pytest.raises(UnsupportedMediaTypeError):
        validator.validate(
            filename="invoice.jpg",
            content_type="application/pdf",
            content_length=100,
            content=b"%PDF-",
        )


def should_accept_filename_at_database_column_limit(
    validator: UploadValidator,
) -> None:
    """Accept a filename that exactly fits the persistence column."""
    validator.validate(
        filename=f"{'a' * 251}.pdf",
        content_type="application/pdf",
        content_length=5,
        content=b"%PDF-",
    )


def should_reject_filename_exceeding_database_column_limit(
    validator: UploadValidator,
) -> None:
    """Reject an otherwise-valid filename before persistence and rate limiting."""
    with pytest.raises(InvalidFilenameError, match="255-character limit"):
        validator.validate(
            filename=f"{'a' * 252}.pdf",
            content_type="application/pdf",
            content_length=5,
            content=b"%PDF-",
        )


def should_reject_empty_pdf(validator: UploadValidator) -> None:
    """Reject empty content even when its metadata claims it is a PDF."""
    with pytest.raises(InvalidPayloadError, match="empty"):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            content_length=0,
            content=b"",
        )


def should_reject_spoofed_pdf_content(validator: UploadValidator) -> None:
    """Reject arbitrary bytes carrying PDF metadata."""
    with pytest.raises(UnsupportedMediaTypeError, match="PDF"):
        validator.validate(
            filename="invoice.pdf",
            content_type="application/pdf",
            content_length=8,
            content=b"MZ\x90\x00fake",
        )


@pytest.fixture
def document_validator() -> UploadValidator:
    """Provide a validator configured for the claim-attachment contract."""
    return UploadValidator(
        max_bytes=CAP_BYTES, allowed_media_types=DOCUMENT_ALLOWED_MEDIA_TYPES
    )


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("receipt.jpg", "image/jpeg", b"\xff\xd8\xff" + b"0" * 20),
        ("receipt.jpeg", "image/jpeg", b"\xff\xd8\xff" + b"0" * 20),
        ("receipt.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"0" * 20),
    ],
)
def should_accept_a_common_image_type_alongside_pdf(
    document_validator: UploadValidator,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    """Accept a photograph of a paper receipt on equal footing with a PDF."""
    document_validator.validate(
        filename=filename,
        content_type=content_type,
        content_length=len(content),
        content=content,
    )


def should_reject_spoofed_image_content(document_validator: UploadValidator) -> None:
    """Reject bytes that don't carry the declared image type's signature."""
    with pytest.raises(UnsupportedMediaTypeError, match="JPEG"):
        document_validator.validate(
            filename="receipt.jpg",
            content_type="image/jpeg",
            content_length=8,
            content=b"MZ\x90\x00fake",
        )


def should_reject_a_media_type_outside_the_document_contract(
    document_validator: UploadValidator,
) -> None:
    """Reject a type that is neither PDF nor a supported image format."""
    with pytest.raises(
        UnsupportedMediaTypeError, match=r"(?=.*PDF)(?=.*JPEG)(?=.*PNG)"
    ):
        document_validator.validate(
            filename="receipt.gif",
            content_type="image/gif",
            content_length=8,
            content=b"GIF89a",
        )
