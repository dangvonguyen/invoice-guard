"""Pure field-by-field comparison of an expected/actual extraction pair.

Exact, typed equality with no fuzzy matching. ``expected`` and ``actual`` are
both :class:`ExtractedInvoice` instances; the returned :class:`CaseScore` carries
every expected/actual pair in serialized form so the artifact writers can emit it
directly.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from app.services.extraction.model import ExtractedInvoice, ExtractedLineItem
from eval.extraction.scoring.constants import LINE_ITEM_SUBFIELDS, SCALAR_FIELDS
from eval.extraction.scoring.models import (
    CaseScore,
    FieldComparison,
    LineItemComparison,
    LineItemRowComparison,
)

# Scalar fields whose string comparison strips only surrounding whitespace.
_STRIPPED_FIELDS = frozenset({"vendor_name", "invoice_number"})
# Scalar fields compared as ``Decimal`` (``None`` stays distinct from zero).
_DECIMAL_FIELDS = frozenset({"tax_amount", "total_amount"})


def compare_case(
    expected: ExtractedInvoice,
    actual: ExtractedInvoice,
    *,
    name: str = "",
    dimensions: Sequence[str] = (),
    confidence: str | None = None,
    confidence_reason: str | None = None,
    latency_ms: int = 0,
) -> CaseScore:
    """Score ``actual`` against ``expected`` for one case."""
    fields = {
        field: _compare_scalar(field, getattr(expected, field), getattr(actual, field))
        for field in SCALAR_FIELDS
    }
    line_items = _compare_line_items(expected.line_items, actual.line_items)
    fully_correct = all(fc.match for fc in fields.values()) and line_items.ordered_match

    return CaseScore(
        name=name,
        dimensions=tuple(dimensions),
        error=None,
        fully_correct=fully_correct,
        confidence=confidence,
        confidence_reason=confidence_reason,
        latency_ms=latency_ms,
        fields=fields,
        line_items=line_items,
    )


def _compare_scalar(field: str, expected: Any, actual: Any) -> FieldComparison:
    return FieldComparison(
        expected=_serialize(expected),
        actual=_serialize(actual),
        match=_scalar_match(field, expected, actual),
    )


def _scalar_match(field: str, expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    if field in _DECIMAL_FIELDS:
        return Decimal(expected) == Decimal(actual)
    if field in _STRIPPED_FIELDS:
        return str(expected).strip() == str(actual).strip()
    return bool(expected == actual)


def _compare_line_items(
    expected: Sequence[ExtractedLineItem], actual: Sequence[ExtractedLineItem]
) -> LineItemComparison:
    rows = [
        LineItemRowComparison(
            index=index,
            fields={
                sub: _compare_line_item_field(
                    sub,
                    expected[index] if index < len(expected) else None,
                    actual[index] if index < len(actual) else None,
                )
                for sub in LINE_ITEM_SUBFIELDS
            },
        )
        for index in range(max(len(expected), len(actual)))
    ]
    ordered_match = len(expected) == len(actual) and all(
        fc.match for row in rows for fc in row.fields.values()
    )
    unordered_match = Counter(_row_key(li) for li in expected) == Counter(
        _row_key(li) for li in actual
    )
    return LineItemComparison(
        ordered_match=ordered_match,
        unordered_match=unordered_match,
        expected_count=len(expected),
        actual_count=len(actual),
        rows=rows,
    )


def _compare_line_item_field(
    sub: str, expected: ExtractedLineItem | None, actual: ExtractedLineItem | None
) -> FieldComparison:
    expected_value = getattr(expected, sub) if expected is not None else None
    actual_value = getattr(actual, sub) if actual is not None else None
    if expected_value is None or actual_value is None:
        match = expected_value is None and actual_value is None
    elif sub == "description":
        match = expected_value == actual_value
    else:
        match = Decimal(expected_value) == Decimal(actual_value)
    return FieldComparison(
        expected=_serialize(expected_value),
        actual=_serialize(actual_value),
        match=match,
    )


def _row_key(item: ExtractedLineItem) -> tuple[Any, ...]:
    return tuple(getattr(item, sub) for sub in LINE_ITEM_SUBFIELDS)


def _serialize(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)
