"""Vocabularies shared across the generation package."""

from typing import Final

# Semantic label slots a template may print. ``label_overrides`` keys in
# ``case.yaml`` must be a subset of this set; every template's ``default_labels``
# must cover it in full so a template never falls back to a literal.
LABEL_SLOTS: Final = frozenset(
    {
        "invoice_number",
        "invoice_date",
        "subtotal",
        "tax_amount",
        "total_amount",
        "line_item_qty",
        "line_item_unit_price",
        "line_item_amount",
        "vendor_party",
        "buyer_party",
    }
)

# Default printed string for every slot in ``LABEL_SLOTS``.
BASE_LABELS: Final[dict[str, str]] = {
    "invoice_number": "Invoice No.",
    "invoice_date": "Invoice Date",
    "subtotal": "Subtotal",
    "tax_amount": "Tax",
    "total_amount": "Total",
    "line_item_qty": "Qty",
    "line_item_unit_price": "Unit Price",
    "line_item_amount": "Amount",
    "vendor_party": "From",
    "buyer_party": "Bill To",
}

# Closed vocabulary of formatting/structural dimension tags authors may list in
# ``case.yaml``. Taken verbatim from the dimension roster in the golden-set spec.
DIMENSIONS: Final = frozenset(
    {
        # -- Amount formatting --
        "comma-grouped-amount",  # "2,797.20"
        "symbol-formatted-amount",  # "$1,234.56" / "€1,234.56"
        # -- Date --
        "iso-date",  # 2024-03-15
        "us-slash-date",  # 03/15/2024 (MM/DD/YYYY)
        "eu-slash-date",  # 15/03/2024 (DD/MM/YYYY)
        "dotted-date",  # 15.03.2024 (DD.MM.YYYY)
        "long-month-date",  # "March 15, 2024"
        "ambiguous-date",  # 07/03/2024 -> Jul 3 or Mar 7
        # -- Tax presence --
        "zero-tax",  # tax_amount "0.00"
        "no-tax-line",  # tax_amount null
        # -- Line-item semantics --
        "no-quantity",
        "credit-line",  # item with a negative amount (discount/refund)
        # -- Page structure that scrambles or misleads reading order --
        "summary-block-before-lines",
        "column-order-amount-first",
        "multi-column-layout",
        "vendor-in-footer",
        "multi-page",
        "itemized-vat",
        # -- Vendor identification traps ("Seller:" / "Client:") --
        "two-candidate-vendors",
        # -- Distractors --
        "distractor-po-number",
        "distractor-bank-account",
        "distractor-ship-to",
    }
)
