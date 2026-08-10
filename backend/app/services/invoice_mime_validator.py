"""Validate uploaded invoice files by declared MIME type and size."""


class InvoiceValidationError(Exception):
    """Base class for invoice upload validation failures."""


class PayloadTooLargeError(InvoiceValidationError):
    """Raised when the file exceeds the configured size cap."""


class UnreadableUploadError(InvoiceValidationError):
    """Raised when required upload metadata is missing."""


class InvoiceMimeValidator:
    """Enforce the Core-scope upload contract: text-native PDF only."""

    def __init__(self, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes

    def validate(
        self, *, filename: str | None, content_type: str | None, size: int | None
    ) -> None:
        """Raise if the upload doesn't satisfy the validation requirements.

        Raises:
            UnreadableUploadError: size could not be determined.
            PayloadTooLargeError: size exceeds the configured cap.
        """
        if size is None:
            raise UnreadableUploadError("upload size could not be determined")
        if size > self._max_bytes:
            raise PayloadTooLargeError(
                f"file exceeds the {self._max_bytes}-byte size cap"
            )
