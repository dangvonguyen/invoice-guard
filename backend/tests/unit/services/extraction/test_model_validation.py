"""Specify how ExtractedInvoice/ExtractedLineItem validate the optional fields."""

from decimal import Decimal

import pytest

from app.services.extraction.model import ExtractedInvoice
from tests.support.constants import RAW_INVOICE_DATA

pytestmark = pytest.mark.unit


def should_default_invoice_number_and_line_item_pricing_fields_to_none() -> None:
    """A response omitting the new optional fields validates without them."""
    invoice = ExtractedInvoice.model_validate(RAW_INVOICE_DATA)

    assert invoice.invoice_number is None
    assert all(item.quantity is None for item in invoice.line_items)
    assert all(item.unit_price is None for item in invoice.line_items)


def should_parse_invoice_number_and_line_item_pricing_fields_when_present() -> None:
    """A response with the new optional fields populates them."""
    raw = {
        **RAW_INVOICE_DATA,
        "invoice_number": "INV-1001",
        "line_items": [
            {
                "description": "Widgets",
                "amount": "100.00",
                "quantity": "4",
                "unit_price": "25.00",
            }
        ],
    }

    invoice = ExtractedInvoice.model_validate(raw)

    assert invoice.invoice_number == "INV-1001"
    assert str(invoice.line_items[0].quantity) == "4"
    assert str(invoice.line_items[0].unit_price) == "25.00"


def should_default_tax_amount_to_none_when_omitted() -> None:
    """A response with no tax line at all validates with tax_amount None."""
    raw = {k: v for k, v in RAW_INVOICE_DATA.items() if k != "tax_amount"}

    invoice = ExtractedInvoice.model_validate(raw)

    assert invoice.tax_amount is None


def should_distinguish_a_null_tax_amount_from_a_zero_tax_amount() -> None:
    """`null` (no tax stated) and `"0.00"` (zero tax line printed) are distinct."""
    no_tax = ExtractedInvoice.model_validate({**RAW_INVOICE_DATA, "tax_amount": None})
    zero_tax = ExtractedInvoice.model_validate(
        {**RAW_INVOICE_DATA, "tax_amount": "0.00"}
    )

    assert no_tax.tax_amount is None
    assert zero_tax.tax_amount == Decimal("0.00")


def should_accept_an_explicit_null_for_the_new_optional_fields() -> None:
    """An explicit null (as opposed to an omitted key) is also valid."""
    raw = {
        **RAW_INVOICE_DATA,
        "invoice_number": None,
        "line_items": [
            {
                "description": "Consulting",
                "amount": "100.00",
                "quantity": None,
                "unit_price": None,
            }
        ],
    }

    invoice = ExtractedInvoice.model_validate(raw)

    assert invoice.invoice_number is None
    assert invoice.line_items[0].quantity is None
    assert invoice.line_items[0].unit_price is None
