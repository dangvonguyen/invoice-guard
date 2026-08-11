"""Validate uploaded invoice files by declared MIME type and size."""

from collections.abc import Mapping


class InvoiceValidationError(Exception):
    """Base class for invoice upload validation failures."""


class PayloadTooLargeError(InvoiceValidationError):
    """Raised when the file exceeds the configured size cap."""


class UnreadableUploadError(InvoiceValidationError):
    """Raised when required upload metadata is missing."""


class InvalidFilenameError(InvoiceValidationError):
    """Raised when the upload filename cannot be safely persisted."""


class UnsupportedMediaTypeError(InvoiceValidationError):
    """Raised when the declared type or extension isn't (yet) accepted."""


_DEFAULT_ALLOWED_TYPES: Mapping[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
}
_MAX_FILENAME_LENGTH = 255


class InvoiceMimeValidator:
    """Enforce the Core-scope upload contract: text-native PDF only."""

    def __init__(
        self,
        max_bytes: int = 10 * 1024 * 1024,
        allowed_types: Mapping[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._allowed_types = dict(allowed_types or _DEFAULT_ALLOWED_TYPES)

    def validate(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        size: int | None,
        content: bytes,
    ) -> None:
        """Raise if the upload doesn't satisfy the validation requirements.

        Raises:
            UnsupportedMediaTypeError: declared type isn't allowed, or the
                filename extension disagrees with the declared type.
            UnreadableUploadError: size could not be determined.
            InvalidFilenameError: filename exceeds the persistence limit.
            PayloadTooLargeError: size exceeds the configured cap.
        """
        allowed_extensions = self._allowed_types.get(content_type or "")
        if allowed_extensions is None:
            raise UnsupportedMediaTypeError(
                f"{content_type or 'unknown content type'} is not yet "
                "supported; PDF is the only currently supported format"
            )
        if filename is None or not filename.lower().endswith(allowed_extensions):
            raise UnsupportedMediaTypeError(
                "file extension does not match its declared content type"
            )
        if len(filename) > _MAX_FILENAME_LENGTH:
            raise InvalidFilenameError(
                f"filename exceeds the {_MAX_FILENAME_LENGTH}-character limit"
            )
        if size is None:
            raise UnreadableUploadError("upload size could not be determined")
        if size > self._max_bytes:
            raise PayloadTooLargeError(
                f"file exceeds the {self._max_bytes}-byte size cap"
            )
        if not content:
            raise UnreadableUploadError("upload is empty")
        if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
            raise UnsupportedMediaTypeError("file content is not a PDF document")
