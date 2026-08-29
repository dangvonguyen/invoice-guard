"""The closed set of fields the scorer compares."""

from typing import Final

# Scalar fields scored by typed, exact equality
SCALAR_FIELDS: Final = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "currency",
    "tax_amount",
    "total_amount",
)

# The four line-item subfields compared
LINE_ITEM_SUBFIELDS: Final = ("description", "amount", "quantity", "unit_price")
