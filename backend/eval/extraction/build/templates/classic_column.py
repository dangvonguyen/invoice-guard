"""``classic-column`` -- the baseline layout."""

from collections.abc import Mapping

from eval.extraction.build.source import SourceDocument
from eval.extraction.build.templates._base import Template
from eval.extraction.build.templates._blocks import (
    meta_panel,
    new_pdf,
    party_block,
    title,
)
from eval.extraction.build.templates._money import date_doc_str
from eval.extraction.build.templates._sections import (
    qty_unit_amount_table,
    standard_totals,
)
from eval.extraction.build.vocab import BASE_LABELS

DESCRIPTION = (
    "Vendor header, top-right meta panel, Qty/Unit price/Amount columns, "
    "totals below the lines."
)


def render(doc: SourceDocument, labels: Mapping[str, str]) -> bytes:
    pdf = new_pdf(page_size="letter")
    title(pdf, "INVOICE")
    party_block(
        pdf,
        label=labels["vendor_party"],
        name=doc.vendor.name,
        address=doc.vendor.address,
        contact=doc.vendor.contact,
    )

    meta: list[tuple[str, str]] = []
    if doc.invoice.number is not None:
        meta.append((labels["invoice_number"], doc.invoice.number))
    meta.append((labels["invoice_date"], date_doc_str(doc)))
    meta_panel(pdf, rows=meta)

    qty_unit_amount_table(pdf, doc, labels)
    standard_totals(pdf, doc, labels)

    return bytes(pdf.output())


TEMPLATE = Template(
    name="classic-column",
    description=DESCRIPTION,
    optional_slots=frozenset(),
    default_labels=dict(BASE_LABELS),
    render=render,
)
