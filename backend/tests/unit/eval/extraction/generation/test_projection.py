"""Specify the authored-data -> ``expected.json`` projection."""

from collections.abc import Callable

import pytest

from eval.extraction.generation.models import SourceDocument
from eval.extraction.generation.projection import project

DocFactory = Callable[..., SourceDocument]

pytestmark = pytest.mark.unit


def should_keep_the_extraction_field_subset_verbatim(make_doc: DocFactory) -> None:
    doc = make_doc()

    result = project(doc)

    assert result == {
        "vendor_name": "Acme Supplies Ltd",
        "invoice_number": "INV-2024-0042",
        "invoice_date": "2024-03-07",
        "currency": "USD",
        "tax_amount": "10.00",
        "total_amount": "110.00",
        "line_items": [
            {
                "description": "Consulting services",
                "amount": "100.00",
                "quantity": "4",
                "unit_price": "25.00",
            }
        ],
    }


def should_drop_buyer_distractors_and_render_only_line_fields(
    make_doc: DocFactory,
) -> None:
    doc = make_doc(
        buyer={"name": "Globex Corp"},
        distractors={"po_number": "PO-1", "bank_account": "GB00"},
        line_items=[
            {
                "description": "Widget",
                "amount": "100.00",
                "quantity": "4",
                "unit_price": "25.00",
                "unit": "ea",
                "vat_rate": "20",
            }
        ],
    )

    result = project(doc)

    assert "buyer" not in result
    assert "distractors" not in result
    assert set(result["line_items"][0]) == {
        "description",
        "amount",
        "quantity",
        "unit_price",
    }


def should_preserve_authored_line_order(make_doc: DocFactory) -> None:
    doc = make_doc(
        line_items=[
            {"description": "First", "amount": "10.00"},
            {"description": "Second", "amount": "20.00"},
            {"description": "Third", "amount": "80.00"},
        ],
        invoice={"tax_amount": None, "total_amount": "110.00"},
    )

    descriptions = [li["description"] for li in project(doc)["line_items"]]

    assert descriptions == ["First", "Second", "Third"]


def should_keep_null_invoice_number_and_tax(make_doc: DocFactory) -> None:
    doc = make_doc(
        invoice={"number": None, "tax_amount": None, "total_amount": "100.00"}
    )

    result = project(doc)

    assert result["invoice_number"] is None
    assert result["tax_amount"] is None
