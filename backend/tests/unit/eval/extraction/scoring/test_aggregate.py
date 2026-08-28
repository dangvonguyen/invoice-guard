"""Specify how per-case scores roll up into run totals and dimension slices."""

from collections.abc import Callable

import pytest

from app.services.extraction.model import ExtractedInvoice
from eval.extraction.scoring.aggregate import aggregate
from eval.extraction.scoring.compare import compare_case
from eval.extraction.scoring.models import CaseScore

pytestmark = pytest.mark.unit

InvoiceFactory = Callable[..., ExtractedInvoice]


@pytest.fixture
def scores(make_invoice: InvoiceFactory) -> list[CaseScore]:
    perfect = compare_case(
        make_invoice(), make_invoice(), name="a_perfect", dimensions=["iso-date"]
    )
    wrong_vendor = compare_case(
        make_invoice(vendor_name="Right Co."),
        make_invoice(vendor_name="Wrong Co."),
        name="b_wrong_vendor",
        dimensions=["iso-date", "eu-slash-date"],
    )
    errored = CaseScore.errored(
        "c_errored",
        ["eu-slash-date"],
        "model did not return a schema-valid response",
        latency_ms=10,
        expected_line_count=2,
    )
    return [perfect, wrong_vendor, errored]


def should_count_correct_over_total_for_every_field(scores: list[CaseScore]) -> None:
    totals = aggregate(scores)

    assert totals.cases == 3
    assert totals.field_accuracy["vendor_name"].correct == 1
    assert totals.field_accuracy["vendor_name"].total == 3
    assert totals.field_accuracy["invoice_number"].correct == 2
    assert totals.field_accuracy["invoice_number"].total == 3


def should_derive_fully_correct_and_error_rates(scores: list[CaseScore]) -> None:
    totals = aggregate(scores)

    assert totals.fully_correct == 1
    assert totals.fully_correct_rate == pytest.approx(0.3333)
    assert totals.error_count == 1
    assert totals.error_rate == pytest.approx(0.3333)


def should_fold_an_errored_case_into_the_line_item_field_denominator(
    scores: list[CaseScore],
) -> None:
    totals = aggregate(scores)

    line_item_fields = totals.field_accuracy["line_item_fields"]
    assert line_item_fields.correct == 0
    assert line_item_fields.total == 8
    assert totals.field_accuracy["line_items_ordered"].correct == 2


def should_slice_each_dimension_over_exactly_its_tagged_cases(
    scores: list[CaseScore],
) -> None:
    totals = aggregate(scores)

    iso = totals.by_dimension["iso-date"]
    assert iso.cases == 2
    assert iso.fully_correct == 1
    assert iso.error_count == 0
    assert iso.field_accuracy["vendor_name"].correct == 1

    eu = totals.by_dimension["eu-slash-date"]
    assert eu.cases == 2
    assert eu.error_count == 1
    assert eu.fully_correct == 0


def should_omit_dimensions_no_scored_case_carries(scores: list[CaseScore]) -> None:
    totals = aggregate(scores)

    assert set(totals.by_dimension) == {"iso-date", "eu-slash-date"}
