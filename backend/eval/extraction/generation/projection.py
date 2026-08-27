"""Project authored data into the ``expected.json`` ground truth.

The projection is a trivial identity over the ``ExtractedInvoice`` field subset:
canonical strings pass through unchanged, the date is already ISO, line items
keep their authored order, and ``buyer`` / ``distractors`` / the render-only line
fields are dropped. Arithmetic self-checks run here unless a case opts out.
"""

from decimal import Decimal
from typing import Any

from eval.extraction.generation.models import SourceDocument


class CheckFailure(ValueError):
    """An authored-data arithmetic self-check did not hold."""


def project(doc: SourceDocument) -> dict[str, Any]:
    """Return the ``expected.json`` dict, running the enabled self-checks first."""
    if doc.checks.line_arithmetic:
        _check_line_arithmetic(doc)
    if doc.checks.total_reconciliation:
        _check_total_reconciliation(doc)

    return {
        "vendor_name": doc.vendor.name,
        "invoice_number": doc.invoice.number,
        "invoice_date": doc.invoice.date.isoformat(),
        "currency": doc.invoice.currency,
        "tax_amount": doc.invoice.tax_amount,
        "total_amount": doc.invoice.total_amount,
        "line_items": [
            {
                "description": li.description,
                "amount": li.amount,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
            }
            for li in doc.line_items
        ],
    }


def _check_line_arithmetic(doc: SourceDocument) -> None:
    for index, li in enumerate(doc.line_items):
        if li.quantity is None or li.unit_price is None:
            continue
        expected = Decimal(li.quantity) * Decimal(li.unit_price)
        if expected != Decimal(li.amount):
            raise CheckFailure(
                f"line {index} ({li.description!r}): "
                f"quantity*unit_price = {expected} but amount = {li.amount}"
            )


def _check_total_reconciliation(doc: SourceDocument) -> None:
    tax = (
        Decimal(doc.invoice.tax_amount)
        if doc.invoice.tax_amount is not None
        else Decimal("0")
    )
    line_sum = sum((Decimal(li.amount) for li in doc.line_items), Decimal("0"))
    if line_sum + tax != Decimal(doc.invoice.total_amount):
        raise CheckFailure(
            f"sum(line amounts) {line_sum} + tax {tax} = {line_sum + tax} "
            f"but total_amount = {doc.invoice.total_amount}"
        )
