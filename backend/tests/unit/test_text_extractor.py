"""Specify how text is extracted from a stored PDF's bytes."""

import pytest
from fpdf import FPDF

from app.services.text_extractor import NoTextLayerError, PdfTextExtractor

pytestmark = pytest.mark.unit


def pdf_with_text(text: str) -> bytes:
    """Build a real, parseable PDF containing the given text."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text=text)
    return bytes(pdf.output())


def blank_pdf() -> bytes:
    """Build a real, parseable PDF with a page but no text content."""
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())


@pytest.fixture
def extractor() -> PdfTextExtractor:
    return PdfTextExtractor()


def should_extract_text_present_in_a_text_native_pdf(
    extractor: PdfTextExtractor,
) -> None:
    """Return the text embedded in a PDF with a real text layer."""
    content = pdf_with_text("Vendor: Acme Supplies\nTotal: 482.10 USD")

    text = extractor.extract_text(content)

    assert "Acme Supplies" in text
    assert "482.10" in text


def should_raise_when_the_pdf_has_no_text_layer(
    extractor: PdfTextExtractor,
) -> None:
    """Reject a PDF whose pages carry no extractable text (e.g. a scan)."""
    with pytest.raises(NoTextLayerError):
        extractor.extract_text(blank_pdf())
