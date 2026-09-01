"""Synthetic ``SourceDocument`` factories for the generation unit tests."""

import copy
from collections.abc import Callable
from typing import Any

import pytest

from eval.extraction.build.source import SourceDocument

_BASE: dict[str, Any] = {
    "vendor": {
        "name": "Acme Supplies Ltd",
        "address": ["10 Mill Street", "Leeds LS1 4AB"],
        "contact": ["ap@acme.example"],
    },
    "invoice": {
        "number": "INV-2024-0042",
        "date": "2024-03-07",
        "currency": "USD",
        "tax_amount": "10.00",
        "total_amount": "110.00",
    },
    "line_items": [
        {
            "description": "Consulting services",
            "amount": "100.00",
            "quantity": "4",
            "unit_price": "25.00",
        },
    ],
    "render": {
        "date_format": "iso",
        "amount_grouping": True,
        "currency_display": "code",
    },
}

DocFactory = Callable[..., SourceDocument]


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


@pytest.fixture
def make_doc() -> DocFactory:
    """Return a factory: ``make_doc(**top_level_overrides) -> SourceDocument``."""

    def factory(**overrides: Any) -> SourceDocument:
        return SourceDocument.model_validate(_merge(_BASE, overrides))

    return factory
