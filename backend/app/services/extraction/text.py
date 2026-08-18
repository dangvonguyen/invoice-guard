"""Extract raw text from a stored PDF's bytes."""

from io import BytesIO
from typing import Protocol

from pypdf import PdfReader

from app.core.errors import DomainError


class NoTextLayerError(DomainError):
    """Raised when a PDF has no extractable text on any page."""

    code = "NO_TEXT_LAYER"
    status_code = 422


class TextExtractor(Protocol):
    """Extract an embedded text layer from an invoice document."""

    def extract_text(self, *, content: bytes) -> str:
        """Return the document's embedded text."""
        ...


class PdfTextExtractor:
    """Read the text layer out of a PDF's bytes."""

    def extract_text(self, content: bytes) -> str:
        """Return the concatenated text of every page.

        Raises:
            NoTextLayerError: no page yielded any extractable text (e.g. a
                scanned, image-only PDF).
        """
        reader = PdfReader(BytesIO(content))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages_text)
        if not text.strip():
            raise NoTextLayerError("PDF has no extractable text layer")
        return text
