"""Specify the layout templates directly: determinism and distractor placement."""

from collections.abc import Callable
from typing import Any

import pytest

from app.services.extraction.text import PdfTextExtractor
from eval.extraction.build.source import SourceDocument
from eval.extraction.build.templates import TEMPLATES
from eval.extraction.build.templates._base import Template

DocFactory = Callable[..., SourceDocument]

pytestmark = pytest.mark.unit

_extractor = PdfTextExtractor()

# A document valid for every template (carries a buyer, VAT and every distractor;
# templates ignore what they do not place).
_KITCHEN_SINK: dict[str, Any] = {
    "buyer": {"name": "Globex Corp", "address": ["1 Globex Plaza"]},
    "line_items": [
        {
            "description": "Consulting services",
            "amount": "100.00",
            "quantity": "4",
            "unit_price": "25.00",
            "unit": "hrs",
            "vat_rate": "10",
        }
    ],
    "distractors": {
        "po_number": "PO-1",
        "bank_account": "GB00BANK",
        "ship_to": {"name": "Globex Warehouse", "address": ["7 Dock Road"]},
    },
}

_SENTINELS: dict[str, tuple[str, dict[str, Any]]] = {
    "buyer": ("Zulu Buyer Sentinel", {"buyer": {"name": "Zulu Buyer Sentinel"}}),
    "po_number": (
        "ZULU-PO-SENTINEL",
        {"distractors": {"po_number": "ZULU-PO-SENTINEL"}},
    ),
    "bank_account": (
        "ZULUBANKSENTINEL",
        {"distractors": {"bank_account": "ZULUBANKSENTINEL"}},
    ),
    "ship_to": (
        "Zulu Ship Sentinel",
        {"distractors": {"ship_to": {"name": "Zulu Ship Sentinel"}}},
    ),
}

_SLOT_CASES = [(t, slot) for t in TEMPLATES for slot in sorted(t.optional_slots)]


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def should_render_identical_bytes_on_repeat(
    template: Template, make_doc: DocFactory
) -> None:
    doc = make_doc(**_KITCHEN_SINK)

    first = template.render(doc, template.default_labels)
    second = template.render(doc, template.default_labels)

    assert first == second


@pytest.mark.parametrize(
    ("template", "slot"), _SLOT_CASES, ids=[f"{t.name}-{s}" for t, s in _SLOT_CASES]
)
def should_place_every_declared_slot_in_the_extracted_text(
    template: Template, slot: str, make_doc: DocFactory
) -> None:
    value, overrides = _SENTINELS[slot]
    if "buyer" in template.optional_slots and "buyer" not in overrides:
        overrides = {**overrides, "buyer": {"name": "Globex Corp"}}

    doc = make_doc(**overrides)
    text = _extractor.extract_text(template.render(doc, template.default_labels))

    assert value in text
