"""Specify how extracted values are checked against source document text."""

import pytest

from app.services.extraction.grounding import GroundingChecker

pytestmark = pytest.mark.unit


@pytest.fixture
def checker() -> GroundingChecker:
    return GroundingChecker()


def should_accept_a_value_that_appears_verbatim_in_source_text(
    checker: GroundingChecker,
) -> None:
    """A value found exactly in the source text is grounded."""
    assert checker.is_grounded(value="482.10", source_text="Total: 482.10 USD") is True


def should_reject_a_value_absent_from_source_text(
    checker: GroundingChecker,
) -> None:
    """A value never mentioned anywhere in the source text is not grounded."""
    assert checker.is_grounded(value="999.00", source_text="Total: 482.10 USD") is False


def should_normalize_whitespace_before_comparing(
    checker: GroundingChecker,
) -> None:
    """Differences in whitespace/newlines alone don't break grounding."""
    assert checker.is_grounded(
        value="Acme  Supplies", source_text="Vendor:\nAcme\nSupplies\n"
    )


def should_be_case_insensitive(checker: GroundingChecker) -> None:
    """A value that differs only in letter case is still grounded."""
    assert checker.is_grounded(
        value="ACME SUPPLIES", source_text="vendor: acme supplies"
    )
