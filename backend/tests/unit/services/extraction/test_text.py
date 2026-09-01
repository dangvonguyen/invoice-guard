"""Specify how text is extracted from a stored PDF's bytes."""

import pytest

from app.services.extraction.text import NoTextLayerError, PdfTextExtractor
from tests.support.helpers import pdf_bytes

pytestmark = pytest.mark.unit


@pytest.fixture
def extractor() -> PdfTextExtractor:
    return PdfTextExtractor()


def should_extract_text_present_in_a_text_native_pdf(
    extractor: PdfTextExtractor,
) -> None:
    """Return the text embedded in a PDF with a real text layer."""
    content = pdf_bytes("Vendor: Acme Supplies\nTotal: 482.10 USD")

    text = extractor.extract_text(content)

    assert "Acme Supplies" in text
    assert "482.10" in text


def should_raise_when_the_pdf_has_no_text_layer(
    extractor: PdfTextExtractor,
) -> None:
    """Reject a PDF whose pages carry no extractable text (e.g. a scan)."""
    with pytest.raises(NoTextLayerError):
        extractor.extract_text(pdf_bytes())
