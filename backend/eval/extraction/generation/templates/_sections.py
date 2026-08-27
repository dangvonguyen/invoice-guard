"""Composite sections reused across several linear templates."""

from collections.abc import Mapping

from fpdf import FPDF

from eval.extraction.generation.models import SourceDocument
from eval.extraction.generation.templates._blocks import (
    Column,
    line_item_table,
    totals_block,
)
from eval.extraction.generation.templates._money import amount_fn, money_fn


def qty_unit_amount_table(
    pdf: FPDF, doc: SourceDocument, labels: Mapping[str, str]
) -> None:
    """The ``Description | Qty | Unit price | Amount`` line table."""
    amount = amount_fn(doc)
    columns = (
        Column("Description", "LEFT", 3.4),
        Column(labels["line_item_qty"], "RIGHT", 1.0),
        Column(labels["line_item_unit_price"], "RIGHT", 1.3),
        Column(labels["line_item_amount"], "RIGHT", 1.3),
    )
    rows = [
        [
            li.description,
            li.quantity or "",
            amount(li.unit_price) if li.unit_price is not None else "",
            amount(li.amount),
        ]
        for li in doc.line_items
    ]
    line_item_table(pdf, columns=columns, rows=rows)


def standard_totals(pdf: FPDF, doc: SourceDocument, labels: Mapping[str, str]) -> None:
    """Subtotal, optional tax, then total -- all in full currency."""
    money = money_fn(doc)
    rows: list[tuple[str, str]] = [(labels["subtotal"], money(doc.subtotal))]
    if doc.invoice.tax_amount is not None:
        rows.append((labels["tax_amount"], money(doc.invoice.tax_amount)))
    rows.append((labels["total_amount"], money(doc.invoice.total_amount)))
    totals_block(pdf, rows=rows)
