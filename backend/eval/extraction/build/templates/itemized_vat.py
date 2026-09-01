"""``itemized-vat`` -- EU-style itemized VAT invoice with a per-rate summary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal

from fpdf import FPDF

from eval.extraction.build.source import SourceDocument, SourceLineItem
from eval.extraction.build.templates._base import Template
from eval.extraction.build.templates._blocks import (
    Column,
    line_item_table,
    meta_panel,
    new_pdf,
    party_block,
    section,
    side_by_side,
    title,
)
from eval.extraction.build.templates._money import (
    amount_doc_fn,
    date_doc_str,
    money_doc_fn,
)
from eval.extraction.build.vocab import BASE_LABELS

DESCRIPTION = (
    "EU itemized-VAT invoice: No./Description/Qty/UM/Net price/Net worth/VAT %/"
    "Gross worth columns, a VAT-by-rate summary, 2-column scramble Seller/Client "
    "party blocks."
)

_CENT = Decimal("0.01")
AmountFn = Callable[[str], str]
MoneyFn = Callable[[str], str]


def render(doc: SourceDocument, labels: Mapping[str, str]) -> bytes:
    if doc.buyer is None:
        raise ValueError("itemized-vat requires a buyer block")
    amount_fn = amount_doc_fn(doc)
    money_fn = money_doc_fn(doc)

    pdf = new_pdf()
    title(pdf, "INVOICE")

    meta: list[tuple[str, str]] = []
    if doc.invoice.number is not None:
        meta.append((labels["invoice_number"], doc.invoice.number))
    meta.append((labels["invoice_date"], date_doc_str(doc)))
    meta_panel(pdf, rows=meta, align="LEFT")

    def left(p: FPDF) -> None:
        party_block(
            p,
            label=labels["vendor_party"],
            name=doc.vendor.name,
            address=doc.vendor.address,
            contact=doc.vendor.contact,
        )

    buyer = doc.buyer

    def right(p: FPDF) -> None:
        party_block(
            p,
            label=labels["buyer_party"],
            name=buyer.name,
            address=buyer.address,
            contact=buyer.contact,
        )

    side_by_side(pdf, left=left, right=right)

    section(pdf, "ITEMS")
    columns = (
        Column("No.", "LEFT", 0.6),
        Column("Description", "LEFT", 3.0),
        Column(labels["line_item_qty"], "RIGHT", 0.8),
        Column("UM", "LEFT", 0.7),
        Column("Net price", "RIGHT", 1.1),
        Column("Net worth", "RIGHT", 1.1),
        Column("VAT %", "RIGHT", 0.8),
        Column("Gross worth", "RIGHT", 1.2),
    )
    rows = [
        _line_row(doc, li, index, amount_fn)
        for index, li in enumerate(doc.line_items, start=1)
    ]
    line_item_table(pdf, columns=columns, rows=rows)

    section(pdf, "SUMMARY")
    _vat_summary(pdf, doc, amount_fn, money_fn)

    return bytes(pdf.output())


def _line_row(
    doc: SourceDocument, li: SourceLineItem, index: int, amount: AmountFn
) -> list[str]:
    has_vat = li.vat_rate is not None
    return [
        f"{index}.",
        li.description,
        li.quantity or "",
        li.unit or "",
        amount(li.unit_price) if li.unit_price is not None else "",
        amount(li.amount),
        f"{li.vat_rate}%" if has_vat else "",
        amount(doc.gross(li)) if has_vat else amount(li.amount),
    ]


def _vat_summary(
    pdf: FPDF, doc: SourceDocument, amount_fn: AmountFn, money_fn: MoneyFn
) -> None:
    by_rate: dict[str, list[SourceLineItem]] = {}
    for li in doc.line_items:
        if li.vat_rate is None:
            continue
        by_rate.setdefault(li.vat_rate, []).append(li)
    if not by_rate:
        return

    columns = (
        Column("", "LEFT", 1.0),
        Column("VAT %", "RIGHT", 1.0),
        Column("Net Worth", "RIGHT", 1.0),
        Column("VAT", "RIGHT", 1.0),
        Column("Gross Worth", "RIGHT", 1.0),
    )
    rows: list[list[str]] = []
    total_net = Decimal("0")
    total_vat = Decimal("0")
    total_gross = Decimal("0")
    for rate in sorted(by_rate, key=Decimal):
        items = by_rate[rate]
        net = sum((Decimal(i.amount) for i in items), Decimal("0"))
        vat = sum((Decimal(doc.vat_of(i)) for i in items), Decimal("0"))
        gross = sum((Decimal(doc.gross(i)) for i in items), Decimal("0"))
        total_net += net
        total_vat += vat
        total_gross += gross
        rows.append(
            [
                "",
                f"{rate}%",
                amount_fn(f"{net.quantize(_CENT)}"),
                amount_fn(f"{vat.quantize(_CENT)}"),
                amount_fn(f"{gross.quantize(_CENT)}"),
            ]
        )
    rows.append(
        [
            "Total",
            "",
            money_fn(f"{total_net.quantize(_CENT)}"),
            money_fn(f"{total_vat.quantize(_CENT)}"),
            money_fn(f"{total_gross.quantize(_CENT)}"),
        ]
    )
    line_item_table(pdf, columns=columns, rows=rows)


TEMPLATE = Template(
    name="itemized-vat",
    description=DESCRIPTION,
    optional_slots=frozenset({"buyer"}),
    default_labels={
        **BASE_LABELS,
        "vendor_party": "Seller:",
        "buyer_party": "Client:",
        "invoice_date": "Date of issue:",
    },
    render=render,
)
