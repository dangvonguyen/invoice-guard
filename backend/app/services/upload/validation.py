"""Validate uploaded documents by type, filename, content, and size."""

from collections.abc import Mapping
from pathlib import PurePath
from typing import Final

from app.core.errors import DomainError


class InvalidUploadError(DomainError):
    """Base class for upload validation failures."""

    code = "INVALID_UPLOAD"
    status_code = 400


class PayloadTooLargeError(InvalidUploadError):
    """Raised when an upload exceeds the configured size limit."""

    code = "PAYLOAD_TOO_LARGE"
    status_code = 413


class InvalidPayloadError(InvalidUploadError):
    """Raised when an upload payload is missing or invalid."""


class InvalidFilenameError(InvalidUploadError):
    """Raised when an upload filename is invalid or unsafe."""


class UnsupportedMediaTypeError(InvalidUploadError):
    """Raised when an upload's media type or content is unsupported."""

    code = "UNSUPPORTED_MEDIA_TYPE"
    status_code = 415


PDF_MEDIA_TYPE: Final = "application/pdf"
JPEG_MEDIA_TYPE: Final = "image/jpeg"
PNG_MEDIA_TYPE: Final = "image/png"

AllowedMediaTypes = Mapping[str, tuple[str, ...]]

_PDF_MEDIA_TYPES: Final[AllowedMediaTypes] = {
    PDF_MEDIA_TYPE: (".pdf",),
}

_IMAGE_MEDIA_TYPES: Final[AllowedMediaTypes] = {
    JPEG_MEDIA_TYPE: (".jpg", ".jpeg"),
    PNG_MEDIA_TYPE: (".png",),
}

DEFAULT_ALLOWED_MEDIA_TYPES: Final[AllowedMediaTypes] = _PDF_MEDIA_TYPES

DOCUMENT_ALLOWED_MEDIA_TYPES: Final[AllowedMediaTypes] = {
    **_PDF_MEDIA_TYPES,
    **_IMAGE_MEDIA_TYPES,
}


_MEDIA_TYPE_LABELS: Final[Mapping[str, str]] = {
    PDF_MEDIA_TYPE: "PDF",
    JPEG_MEDIA_TYPE: "JPEG",
    PNG_MEDIA_TYPE: "PNG",
}

_MAGIC_BYTES: Final[Mapping[str, bytes]] = {
    PDF_MEDIA_TYPE: b"%PDF-",
    JPEG_MEDIA_TYPE: b"\xff\xd8\xff",
    PNG_MEDIA_TYPE: b"\x89PNG\r\n\x1a\n",
}

_MAX_FILENAME_LENGTH: Final = 255
_DEFAULT_MAX_UPLOAD_BYTES: Final = 10 * 1024 * 1024


class UploadValidator:
    """Validate uploaded files against an upload policy."""

    def __init__(
        self,
        *,
        max_bytes: int = _DEFAULT_MAX_UPLOAD_BYTES,
        allowed_media_types: AllowedMediaTypes = DEFAULT_ALLOWED_MEDIA_TYPES,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be greater than zero")

        if not allowed_media_types:
            raise ValueError("allowed_media_types must not be empty")

        self._max_bytes = max_bytes
        self._allowed_media_types = dict(allowed_media_types)

    def validate(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        content_length: int | None,
        content: bytes,
    ) -> None:
        """Validate an uploaded file.

        Raises:
            InvalidFilenameError:
                The filename is missing, too long, or unsafe.
            InvalidPayloadError:
                The payload is empty or its size is unavailable/inconsistent.
            PayloadTooLargeError:
                The payload exceeds the configured size limit.
            UnsupportedMediaTypeError:
                The media type, extension, or file signature is unsupported.
        """
        normalized_content_type = self._normalize_content_type(content_type)

        self._validate_filename(filename)

        allowed_extensions = self._get_allowed_extensions(normalized_content_type)

        self._validate_extension(filename, allowed_extensions)
        self._validate_size(content_length, len(content))
        self._validate_content(normalized_content_type, content)

    def _normalize_content_type(self, content_type: str | None) -> str:
        """Normalize a declared MIME type."""
        return (content_type or "").strip().lower()

    def _validate_filename(self, filename: str | None) -> None:
        if not filename:
            raise InvalidFilenameError("filename is required")

        if len(filename) > _MAX_FILENAME_LENGTH:
            raise InvalidFilenameError(
                f"filename exceeds the {_MAX_FILENAME_LENGTH}-character limit"
            )

        if "/" in filename or "\\" in filename:
            raise InvalidFilenameError("filename must not contain path separators")

        if filename in {".", ".."}:
            raise InvalidFilenameError("filename is invalid")

    def _get_allowed_extensions(self, content_type: str) -> tuple[str, ...]:
        extensions = self._allowed_media_types.get(content_type)

        if extensions is not None:
            return extensions

        supported = ", ".join(
            _MEDIA_TYPE_LABELS.get(media_type, media_type)
            for media_type in self._allowed_media_types
        )

        raise UnsupportedMediaTypeError(
            f"{self._display_media_type(content_type)} is not supported; "
            f"supported formats are: {supported}"
        )

    def _validate_extension(
        self,
        filename: str,
        allowed_extensions: tuple[str, ...],
    ) -> None:
        suffix = PurePath(filename).suffix.lower()

        if suffix not in allowed_extensions:
            raise UnsupportedMediaTypeError(
                "file extension does not match its declared content type"
            )

    def _validate_size(
        self,
        content_length: int | None,
        actual_size: int,
    ) -> None:
        if content_length is None:
            raise InvalidPayloadError("upload size could not be determined")

        if content_length < 0:
            raise InvalidPayloadError("upload size cannot be negative")

        if content_length != actual_size:
            raise InvalidPayloadError("upload size does not match the payload")

        if content_length > self._max_bytes:
            raise PayloadTooLargeError(
                f"file exceeds the {self._max_bytes}-byte size limit"
            )

        if content_length == 0:
            raise InvalidPayloadError("upload is empty")

    def _validate_content(
        self,
        content_type: str,
        content: bytes,
    ) -> None:
        signature = _MAGIC_BYTES.get(content_type)

        if signature is None:
            return

        if content.startswith(signature):
            return

        label = _MEDIA_TYPE_LABELS.get(
            content_type, self._display_media_type(content_type)
        )

        raise UnsupportedMediaTypeError(
            f"file content does not match the declared {label} type"
        )

    def _display_media_type(self, content_type: str) -> str:
        return content_type or "unknown content type"
