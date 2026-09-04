"""Specify the claim-submission request contract."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.claim import ClaimCreateRequest
from tests.support.constants import VALID_SUBMISSION_PAYLOAD

pytestmark = [pytest.mark.unit]


def valid_payload(**overrides: Any) -> dict[str, Any]:
    """A complete, valid submission payload as parsed JSON."""
    payload = VALID_SUBMISSION_PAYLOAD.copy()
    payload.update(overrides)
    return payload


def should_accept_a_complete_certified_payload() -> None:
    """Parse a well-formed submission without complaint."""
    request = ClaimCreateRequest.model_validate(valid_payload())

    assert request.expense_title == "Annual Figma subscription"
    assert request.vendor == "Figma Inc."


def should_reject_an_uncertified_submission() -> None:
    """Refuse the request unless the certification flag is exactly true."""
    with pytest.raises(ValidationError):
        ClaimCreateRequest.model_validate(valid_payload(certified=False))


def should_reject_a_blank_expense_title() -> None:
    """Require a non-empty label for what the expense was for."""
    with pytest.raises(ValidationError):
        ClaimCreateRequest.model_validate(valid_payload(expense_title="   "))


def should_reject_a_blank_business_purpose() -> None:
    """Require a non-empty business justification."""
    with pytest.raises(ValidationError):
        ClaimCreateRequest.model_validate(valid_payload(business_purpose="   "))


def should_upper_case_the_currency_code() -> None:
    """Normalize the ISO currency code to upper case."""
    request = ClaimCreateRequest.model_validate(valid_payload(currency="eur"))

    assert request.currency == "EUR"


@pytest.mark.parametrize("bad_total", ["0", "-1.00", "1.234"])
def should_reject_a_non_positive_or_over_precise_total(bad_total: str) -> None:
    """Require a positive amount with at most two decimal places."""
    with pytest.raises(ValidationError):
        ClaimCreateRequest.model_validate(valid_payload(total_amount=bad_total))


def should_reject_an_unknown_category() -> None:
    """Only accept categories from the fixed list."""
    with pytest.raises(ValidationError):
        ClaimCreateRequest.model_validate(valid_payload(category="rocket_fuel"))
