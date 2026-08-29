"""Shared fpdf2 building blocks for the layout templates.

Each helper takes an ``FPDF`` and moves the cursor. The order helpers are called
in *is* the content-stream order, which is the point for the column-order,
block-order and multi-column-scramble dimensions.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

from eval.extraction.generation.templates._fonts import FONT_FAMILY, register_fonts

# Pinned so regeneration is byte-stable across runs and machines.
FIXED_CREATION_DATE = datetime(2024, 1, 1, tzinfo=UTC)
PRODUCER = "invoice-guard golden-set generator"

MARGIN_MM = 15
FOOTER_OFFSET_MM = -28

BODY_SIZE = 10
SMALL_SIZE = 8
LABEL_SIZE = 9
TITLE_SIZE = 16

LINE_H = 5.0
SMALL_LINE_H = 4.0


def new_pdf(*, page_size: str = "A4") -> FPDF:
    """Construct a document with fonts, margins and pinned metadata."""
    pdf = FPDF(format=page_size)
    register_fonts(pdf)
    pdf.set_creation_date(FIXED_CREATION_DATE)
    pdf.set_producer(PRODUCER)
    pdf.set_margin(MARGIN_MM)
    pdf.set_auto_page_break(auto=True, margin=MARGIN_MM)
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)
    pdf.add_page()
    return pdf


@dataclass(frozen=True)
class Column:
    """One line-item table column: header text, alignment and relative width."""

    header: str
    align: str = "LEFT"
    width: float = 1.0


def title(pdf: FPDF, text: str) -> None:
    """Render the document title."""
    pdf.set_font(FONT_FAMILY, style="B", size=TITLE_SIZE)
    pdf.cell(0, LINE_H * 1.6, text=text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)
    pdf.ln(2)


def section(pdf: FPDF, text: str) -> None:
    """Render a new section."""
    pdf.set_font(FONT_FAMILY, style="B", size=BODY_SIZE)
    pdf.cell(0, LINE_H * 1.6, text=text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)


def party_block(
    pdf: FPDF,
    *,
    label: str,
    name: str,
    address: Sequence[str] = (),
    contact: Sequence[str] = (),
) -> None:
    """A labelled party: heading, name, then authored address/contact chrome."""
    pdf.set_font(FONT_FAMILY, style="B", size=LABEL_SIZE)
    pdf.cell(0, LINE_H, text=label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)
    pdf.cell(0, LINE_H, text=name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, size=SMALL_SIZE)
    for row in (*address, *contact):
        pdf.cell(0, SMALL_LINE_H, text=row, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)
    pdf.ln(2)


def meta_panel(
    pdf: FPDF, *, rows: Sequence[tuple[str, str]], align: str = "RIGHT"
) -> None:
    """A stack of ``label  value`` lines (invoice number, date, PO number, ...)."""
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)
    for label, value in rows:
        pdf.cell(
            0,
            LINE_H,
            text=f"{label}  {value}",
            align=align,
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(2)


def line_item_table(
    pdf: FPDF,
    *,
    columns: Sequence[Column],
    rows: Sequence[Sequence[str]],
    size: int = LABEL_SIZE,
    repeat_headings: bool = True,
) -> None:
    """Render a line-item table. Column order is the caller's ``columns`` order."""
    pdf.set_font(FONT_FAMILY, size=size)
    with pdf.table(
        col_widths=tuple(c.width for c in columns),
        text_align=tuple(c.align for c in columns),
        first_row_as_headings=True,
        repeat_headings=1 if repeat_headings else 0,
        headings_style=FontFace(emphasis="BOLD"),
    ) as table:
        table.row([c.header for c in columns])
        for row in rows:
            table.row(list(row))
    pdf.ln(2)


def totals_block(pdf: FPDF, *, rows: Sequence[tuple[str, str]]) -> None:
    """Right-aligned ``label  value`` pairs; caller places it before or after lines."""
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE)
    for label, value in rows:
        pdf.cell(
            0,
            LINE_H,
            text=f"{label}  {value}",
            align="RIGHT",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(2)


def side_by_side(
    pdf: FPDF,
    *,
    left: Callable[[FPDF], None],
    right: Callable[[FPDF], None],
    ratio: tuple[int, int] = (58, 42),
) -> None:
    """Lay two render callables out as columns, emitted left then right.

    The two blocks share a vertical band but are written in separate cursor
    passes, so ``pypdf`` interleaves their lines the way it does on real
    two-column invoices.
    """
    start_y = pdf.get_y()
    left_width = pdf.epw * ratio[0] / (ratio[0] + ratio[1])
    right_x = pdf.l_margin + left_width

    saved_r_margin = pdf.r_margin
    pdf.set_right_margin(pdf.w - right_x)
    pdf.set_xy(pdf.l_margin, start_y)
    left(pdf)
    left_end_y = pdf.get_y()

    pdf.set_right_margin(saved_r_margin)
    pdf.set_xy(right_x, start_y)
    _run_indented(pdf, right, right_x)
    right_end_y = pdf.get_y()

    pdf.set_xy(pdf.l_margin, max(left_end_y, right_end_y))
    pdf.ln(2)


def _run_indented(pdf: FPDF, render: Callable[[FPDF], None], left_x: float) -> None:
    saved_l_margin = pdf.l_margin
    pdf.set_left_margin(left_x)
    try:
        render(pdf)
    finally:
        pdf.set_left_margin(saved_l_margin)
