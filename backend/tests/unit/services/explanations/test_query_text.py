"""Unit tests for the review-flag explanation retrieval query-text builder."""

import pytest

from app.services.explanations.service import _build_query_text

pytestmark = pytest.mark.unit


def should_combine_the_summary_and_evidence_into_one_query_string() -> None:
    query = _build_query_text(
        summary="Invoice currency is not in the allowed set.",
        evidence={"currency": "CHF", "allowed_currencies": ["EUR", "GBP", "USD"]},
    )

    assert "Invoice currency is not in the allowed set." in query
    for currency in ["CHF", "EUR", "GBP", "USD"]:
        assert currency in query
