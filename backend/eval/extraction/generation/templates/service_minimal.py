"""``service-minimal`` -- ``Description | Amount`` only, no quantity columns."""

from __future__ import annotations

from collections.abc import Mapping

from fpdf import FPDF

from eval.extraction.generation.constants import BASE_LABELS
from eval.extraction.generation.models import SourceDocument
from eval.extraction.generation.templates._base import Template
from eval.extraction.generation.templates._blocks import (
    Column,
    line_item_table,
    meta_panel,
    new_pdf,
    party_block,
    side_by_side,
    title,
)
from eval.extraction.generation.templates._money import amount_doc_fn, date_doc_str
from eval.extraction.generation.templates._sections import standard_totals

DESCRIPTION = (
    "Minimal service invoice: Description/Amount columns only, no quantity, "
    "tax line only when stated."
)


def render(doc: SourceDocument, labels: Mapping[str, str]) -> bytes:
    amount = amount_doc_fn(doc)

    pdf = new_pdf()
    title(pdf, "INVOICE")

    def left(p: FPDF) -> None:
        party_block(
            p,
            label=labels["vendor_party"],
            name=doc.vendor.name,
            address=doc.vendor.address,
            contact=doc.vendor.contact,
        )

    def right(p: FPDF) -> None:
        meta: list[tuple[str, str]] = []
        if doc.invoice.number is not None:
            meta.append((labels["invoice_number"], doc.invoice.number))
        meta.append((labels["invoice_date"], date_doc_str(doc)))
        meta_panel(p, rows=meta)

    side_by_side(pdf, left=left, right=right)

    columns = (
        Column("Description", "LEFT", 4.0),
        Column(labels["line_item_amount"], "RIGHT", 1.4),
    )
    rows = [[li.description, amount(li.amount)] for li in doc.line_items]
    line_item_table(pdf, columns=columns, rows=rows)
    standard_totals(pdf, doc, labels)

    return bytes(pdf.output())


TEMPLATE = Template(
    name="service-minimal",
    description=DESCRIPTION,
    optional_slots=frozenset(),
    default_labels=dict(BASE_LABELS),
    render=render,
)
