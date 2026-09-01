"""Specify the field-by-field comparison rules for one golden case."""

from collections.abc import Callable

import pytest

from app.services.extraction.model import ExtractedInvoice
from eval.extraction.score.compare import compare_case

pytestmark = pytest.mark.unit

InvoiceFactory = Callable[..., ExtractedInvoice]

_CHAIR = {
    "description": "Ergonomic mesh chair",
    "amount": "1245.00",
    "quantity": "5",
    "unit_price": "249.00",
}
_DESK = {
    "description": "Sit-stand desk frame",
    "amount": "1220.00",
    "quantity": "2",
    "unit_price": "610.00",
}
_TRAY = {
    "description": "Cable management tray",
    "amount": "125.00",
    "quantity": "10",
    "unit_price": "12.50",
}


def should_mark_an_identical_extraction_fully_correct(
    make_invoice: InvoiceFactory,
) -> None:
    score = compare_case(make_invoice(), make_invoice())

    assert score.fully_correct is True
    assert score.error is None
    assert score.fields is not None
    assert all(fc.match for fc in score.fields.values())


def should_flag_the_offending_field_and_drop_fully_correct_on_a_scalar_miss(
    make_invoice: InvoiceFactory,
) -> None:
    expected = make_invoice(vendor_name="Northwind Traders Inc.")
    actual = make_invoice(vendor_name="Northwind Trading Co.")

    score = compare_case(expected, actual)

    assert score.fully_correct is False
    assert score.fields is not None
    assert score.fields["vendor_name"].match is False
    assert score.fields["vendor_name"].expected == "Northwind Traders Inc."
    assert score.fields["vendor_name"].actual == "Northwind Trading Co."
    assert score.fields["invoice_number"].match is True


def should_treat_decimal_amounts_with_different_scales_as_equal(
    make_invoice: InvoiceFactory,
) -> None:
    score = compare_case(
        make_invoice(tax_amount="207.20"), make_invoice(tax_amount="207.2")
    )

    assert score.fields is not None
    assert score.fields["tax_amount"].match is True
    assert score.fully_correct is True


def should_keep_absent_tax_distinct_from_a_printed_zero(
    make_invoice: InvoiceFactory,
) -> None:
    score = compare_case(make_invoice(tax_amount=None), make_invoice(tax_amount="0.00"))

    assert score.fields is not None
    assert score.fields["tax_amount"].match is False
    assert score.fields["tax_amount"].expected is None
    assert score.fields["tax_amount"].actual == "0.00"


def should_compare_currency_case_sensitively(make_invoice: InvoiceFactory) -> None:
    score = compare_case(make_invoice(currency="USD"), make_invoice(currency="usd"))

    assert score.fields is not None
    assert score.fields["currency"].match is False


def should_ignore_only_surrounding_whitespace_on_vendor_name(
    make_invoice: InvoiceFactory,
) -> None:
    score = compare_case(
        make_invoice(vendor_name="Northwind Traders Inc."),
        make_invoice(vendor_name="  Northwind Traders Inc.  "),
    )

    assert score.fields is not None
    assert score.fields["vendor_name"].match is True


def should_keep_a_missing_invoice_number_distinct_from_empty_string(
    make_invoice: InvoiceFactory,
) -> None:
    score = compare_case(
        make_invoice(invoice_number=None), make_invoice(invoice_number="")
    )

    assert score.fields is not None
    assert score.fields["invoice_number"].match is False


def should_score_matching_line_items_ordered_and_unordered(
    make_invoice: InvoiceFactory,
) -> None:
    rows = [_CHAIR, _DESK, _TRAY]
    score = compare_case(make_invoice(line_items=rows), make_invoice(line_items=rows))

    assert score.line_items is not None
    assert score.line_items.ordered_match is True
    assert score.line_items.unordered_match is True
    assert score.line_items.field_matches == 12
    assert score.line_items.field_total == 12
    assert score.fully_correct is True


def should_report_reordered_line_items_as_unordered_only(
    make_invoice: InvoiceFactory,
) -> None:
    expected = make_invoice(line_items=[_CHAIR, _DESK, _TRAY])
    actual = make_invoice(line_items=[_DESK, _TRAY, _CHAIR])

    score = compare_case(expected, actual)

    assert score.line_items is not None
    assert score.line_items.ordered_match is False
    assert score.line_items.unordered_match is True
    assert score.fully_correct is False


def should_use_the_longer_side_for_the_line_item_field_denominator(
    make_invoice: InvoiceFactory,
) -> None:
    expected = make_invoice(line_items=[_CHAIR, _DESK])
    actual = make_invoice(line_items=[_CHAIR, _DESK, _TRAY])

    score = compare_case(expected, actual)

    assert score.line_items is not None
    assert score.line_items.expected_count == 2
    assert score.line_items.actual_count == 3
    assert score.line_items.field_total == 12
    assert score.line_items.field_matches == 8
    surplus = score.line_items.rows[2]
    assert all(fc.match is False for fc in surplus.fields.values())
    assert score.line_item_field_total == 12
    assert score.line_items.ordered_match is False


def should_compare_a_missing_quantity_against_a_stated_one_as_a_miss(
    make_invoice: InvoiceFactory,
) -> None:
    service_line = {"description": "Consulting", "amount": "500.00"}
    expected = make_invoice(line_items=[service_line])
    actual = make_invoice(
        line_items=[{**service_line, "quantity": "1", "unit_price": "500.00"}]
    )

    score = compare_case(expected, actual)

    assert score.line_items is not None
    row = score.line_items.rows[0]
    assert row.fields["quantity"].match is False
    assert row.fields["quantity"].expected is None
    assert row.fields["unit_price"].match is False
    assert row.fields["description"].match is True
