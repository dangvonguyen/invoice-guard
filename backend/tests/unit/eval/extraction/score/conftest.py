"""Synthetic ``ExtractedInvoice`` factory for the scoring unit tests."""

from collections.abc import Callable
from typing import Any

import pytest

from app.services.extraction.model import ExtractedInvoice

_BASE: dict[str, Any] = {
    "vendor_name": "Northwind Traders Inc.",
    "invoice_number": "NT-2024-0417",
    "invoice_date": "2024-03-15",
    "currency": "USD",
    "tax_amount": "207.20",
    "total_amount": "2797.20",
    "line_items": [],
}

InvoiceFactory = Callable[..., ExtractedInvoice]


@pytest.fixture
def make_invoice() -> InvoiceFactory:
    """Return ``make_invoice(**field_overrides) -> ExtractedInvoice``."""

    def factory(**overrides: Any) -> ExtractedInvoice:
        return ExtractedInvoice.model_validate({**_BASE, **overrides})

    return factory
