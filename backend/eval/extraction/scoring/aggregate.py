"""Pure roll-up of per-case scores into run totals and per-dimension slices."""

from collections.abc import Sequence

from eval.extraction.scoring.constants import SCALAR_FIELDS
from eval.extraction.scoring.models import CaseScore, CaseTally, FieldTally, Totals


def aggregate(results: Sequence[CaseScore]) -> Totals:
    """Return whole-run totals plus a :class:`CaseTally` per dimension tag."""
    base = _tally(results)
    by_dimension = {
        tag: _tally([r for r in results if tag in r.dimensions])
        for tag in _dimension_tags(results)
    }
    return Totals(
        cases=base.cases,
        fully_correct=base.fully_correct,
        error_count=base.error_count,
        field_accuracy=base.field_accuracy,
        by_dimension=by_dimension,
    )


def _tally(results: Sequence[CaseScore]) -> CaseTally:
    total = len(results)
    field_accuracy = {
        field: FieldTally(
            correct=sum(
                1 for r in results if r.fields is not None and r.fields[field].match
            ),
            total=total,
        )
        for field in SCALAR_FIELDS
    }
    field_accuracy["line_items_ordered"] = FieldTally(
        correct=sum(
            1
            for r in results
            if r.line_items is not None and r.line_items.ordered_match
        ),
        total=total,
    )
    field_accuracy["line_items_unordered"] = FieldTally(
        correct=sum(
            1
            for r in results
            if r.line_items is not None and r.line_items.unordered_match
        ),
        total=total,
    )
    field_accuracy["line_item_fields"] = FieldTally(
        correct=sum(r.line_item_field_matches for r in results),
        total=sum(r.line_item_field_total for r in results),
    )
    return CaseTally(
        cases=total,
        fully_correct=sum(1 for r in results if r.fully_correct),
        error_count=sum(1 for r in results if r.is_errored),
        field_accuracy=field_accuracy,
    )


def _dimension_tags(results: Sequence[CaseScore]) -> list[str]:
    seen: dict[str, None] = {}
    for result in results:
        for tag in result.dimensions:
            seen.setdefault(tag, None)
    return list(seen)
