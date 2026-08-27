"""Specify the pure render-time formatters."""

import pytest

from eval.extraction.generation.formatting import (
    format_amount,
    format_currency,
    format_date,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("iso", "2024-03-07"),
        ("us-slash", "03/07/2024"),
        ("eu-slash", "07/03/2024"),
        ("dotted", "07.03.2024"),
        ("long-month", "March 7, 2024"),
    ],
)
def should_render_each_date_style(style: str, expected: str) -> None:
    assert format_date("2024-03-07", style) == expected


def should_reject_an_unknown_date_style() -> None:
    with pytest.raises(ValueError, match="unknown date style"):
        format_date("2024-03-07", "roman-numerals")


@pytest.mark.parametrize(
    ("canonical", "grouping", "expected"),
    [
        ("1245.00", True, "1,245.00"),
        ("1245.00", False, "1245.00"),
        ("999.50", True, "999.50"),
        ("1234567.89", True, "1,234,567.89"),
        ("-1245.00", True, "-1,245.00"),
        ("0.00", True, "0.00"),
    ],
)
def should_group_amounts_only_when_asked(
    canonical: str, grouping: bool, expected: str
) -> None:
    assert format_amount(canonical, grouping=grouping) == expected


@pytest.mark.parametrize(
    ("code", "display", "expected"),
    [
        ("USD", "code", "1,245.00 USD"),
        ("USD", "symbol", "$1,245.00"),
        ("USD", "symbol-and-code", "$1,245.00 USD"),
        ("EUR", "symbol", "€1,245.00"),
        ("EUR", "symbol-and-code", "€1,245.00 EUR"),
        ("SEK", "symbol", "SEK 1,245.00"),
    ],
)
def should_wrap_amount_with_symbol_or_code(
    code: str, display: str, expected: str
) -> None:
    assert format_currency("1,245.00", code, display=display) == expected


def should_reject_an_unknown_currency_display() -> None:
    with pytest.raises(ValueError, match="unknown currency display"):
        format_currency("1,245.00", "USD", display="emoji")
