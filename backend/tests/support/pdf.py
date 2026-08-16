"""Build real, parseable PDF bytes for exercising PDF-handling code in tests."""

from fpdf import FPDF


def pdf_bytes(text: str = "") -> bytes:
    """Build a real, parseable single-page PDF containing the given text."""
    pdf = FPDF()
    pdf.add_page()
    if text:
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text=text)
    return bytes(pdf.output())
