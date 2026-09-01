"""Validate uploaded invoice files by declared MIME type and size."""

from collections.abc import Mapping

from app.core.errors import DomainError


class InvalidUploadError(DomainError):
    """Base class for invoice upload validation failures."""

    code = "INVALID_UPLOAD"
    status_code = 400


class PayloadTooLargeError(InvalidUploadError):
    """Raised when the file exceeds the configured size cap."""

    code = "PAYLOAD_TOO_LARGE"
    status_code = 413


class InvalidPayloadError(InvalidUploadError):
    """Raised when required upload metadata is missing."""


class InvalidFilenameError(InvalidUploadError):
    """Raised when the upload filename cannot be safely persisted."""


class UnsupportedMediaTypeError(InvalidUploadError):
    """Raised when the declared type or extension isn't (yet) accepted."""

    code = "UNSUPPORTED_MEDIA_TYPE"
    status_code = 415


_DEFAULT_ALLOWED_TYPES: Mapping[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
}
_MAX_FILENAME_LENGTH = 255


class UploadValidator:
    """Enforce the Core-scope upload contract: text-native PDF only."""

    def __init__(
        self,
        max_bytes: int = 10 * 1024 * 1024,
        allowed_media_types: Mapping[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._allowed_media_types = dict(allowed_media_types or _DEFAULT_ALLOWED_TYPES)

    def validate(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        content_length: int | None,
        content: bytes,
    ) -> None:
        """Raise if the upload doesn't satisfy the validation requirements.

        Raises:
            UnsupportedMediaTypeError: declared type isn't allowed, or the
                filename extension disagrees with the declared type.
            InvalidPayloadError: size could not be determined.
            InvalidFilenameError: filename exceeds the persistence limit.
            PayloadTooLargeError: size exceeds the configured cap.
        """
        allowed_extensions = self._allowed_media_types.get(content_type or "")
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
        if content_length is None:
            raise InvalidPayloadError("upload size could not be determined")
        if content_length > self._max_bytes:
            raise PayloadTooLargeError(
                f"file exceeds the {self._max_bytes}-byte size cap"
            )
        if not content:
            raise InvalidPayloadError("upload is empty")
        if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
            raise UnsupportedMediaTypeError("file content is not a PDF document")
