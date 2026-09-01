"""Shared render-time money/date closures bound to a document's directives."""

from collections.abc import Callable

from eval.extraction.build.formatting import (
    format_amount,
    format_currency,
    format_date,
)
from eval.extraction.build.source import SourceDocument


def amount_doc_fn(doc: SourceDocument) -> Callable[[str], str]:
    """Return a plain grouped-amount formatter (no symbol)."""
    grouping = doc.render.amount_grouping
    return lambda value: format_amount(value, grouping=grouping)


def money_doc_fn(doc: SourceDocument) -> Callable[[str], str]:
    """Return a full currency formatter (grouping + symbol/code per directives)."""
    grouping = doc.render.amount_grouping
    code = doc.invoice.currency
    display = doc.render.currency_display
    return lambda value: format_currency(
        format_amount(value, grouping=grouping), code, display=display
    )


def date_doc_str(doc: SourceDocument) -> str:
    """Return the invoice date rendered in the case's style."""
    return format_date(doc.invoice.date.isoformat(), doc.render.date_format)
