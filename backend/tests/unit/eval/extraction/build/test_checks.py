"""Specify the arithmetic self-checks and their per-case opt-out."""

from collections.abc import Callable

import pytest

from eval.extraction.build.projection import CheckFailure, project
from eval.extraction.build.source import SourceDocument

DocFactory = Callable[..., SourceDocument]

pytestmark = pytest.mark.unit


def should_flag_a_line_where_quantity_times_unit_price_is_wrong(
    make_doc: DocFactory,
) -> None:
    doc = make_doc(
        line_items=[
            {
                "description": "Widget",
                "amount": "25.00",
                "quantity": "2",
                "unit_price": "10.00",
            }
        ],
        invoice={"tax_amount": None, "total_amount": "25.00"},
    )

    with pytest.raises(CheckFailure, match="quantity\\*unit_price"):
        project(doc)


def should_silence_line_arithmetic_when_the_case_opts_out(
    make_doc: DocFactory,
) -> None:
    doc = make_doc(
        line_items=[
            {
                "description": "Widget",
                "amount": "25.00",
                "quantity": "2",
                "unit_price": "10.00",
            }
        ],
        invoice={"tax_amount": None, "total_amount": "25.00"},
        checks={"line_arithmetic": False},
    )

    assert project(doc)["total_amount"] == "25.00"


def should_flag_a_total_that_does_not_reconcile(make_doc: DocFactory) -> None:
    doc = make_doc(invoice={"tax_amount": "10.00", "total_amount": "999.00"})

    with pytest.raises(CheckFailure, match="total_amount"):
        project(doc)


def should_silence_total_reconciliation_when_the_case_opts_out(
    make_doc: DocFactory,
) -> None:
    doc = make_doc(
        invoice={"tax_amount": "10.00", "total_amount": "999.00"},
        checks={"total_reconciliation": False},
    )

    assert project(doc)["total_amount"] == "999.00"
