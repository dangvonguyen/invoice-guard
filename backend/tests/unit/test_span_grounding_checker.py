"""Specify how extracted values are checked against source document text."""

import pytest

from app.services.span_grounding import SpanGroundingChecker

pytestmark = pytest.mark.unit


@pytest.fixture
def checker() -> SpanGroundingChecker:
    return SpanGroundingChecker()


def should_accept_a_value_that_appears_verbatim_in_source_text(
    checker: SpanGroundingChecker,
) -> None:
    """A value found exactly in the source text is grounded."""
    assert checker.check(value="482.10", source_text="Total: 482.10 USD") is True


def should_reject_a_value_absent_from_source_text(
    checker: SpanGroundingChecker,
) -> None:
    """A value never mentioned anywhere in the source text is not grounded."""
    assert checker.check(value="999.00", source_text="Total: 482.10 USD") is False


def should_normalize_whitespace_before_comparing(
    checker: SpanGroundingChecker,
) -> None:
    """Differences in whitespace/newlines alone don't break grounding."""
    assert checker.check(
        value="Acme  Supplies", source_text="Vendor:\nAcme\nSupplies\n"
    )


def should_be_case_insensitive(checker: SpanGroundingChecker) -> None:
    """A value that differs only in letter case is still grounded."""
    assert checker.check(value="ACME SUPPLIES", source_text="vendor: acme supplies")
