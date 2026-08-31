"""Register the vendored DejaVu Sans family on an FPDF instance."""

from fpdf import FPDF

from eval.extraction.paths import FONTS_DIR

FONT_FAMILY = "DejaVu"

_REGULAR = FONTS_DIR / "DejaVuSans.ttf"
_BOLD = FONTS_DIR / "DejaVuSans-Bold.ttf"


def register_fonts(pdf: FPDF) -> None:
    """Add DejaVu Sans regular and bold so every currency symbol renders."""
    pdf.add_font(FONT_FAMILY, style="", fname=str(_REGULAR))
    pdf.add_font(FONT_FAMILY, style="B", fname=str(_BOLD))
