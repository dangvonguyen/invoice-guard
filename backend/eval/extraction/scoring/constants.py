"""Fixed vocabularies and tunables for the scoring harness."""

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

# Aggregate keys carrying the rolled-up line-item results
LINE_ITEM_AGGREGATE_FIELDS: Final = (
    "line_items_ordered",
    "line_items_unordered",
    "line_item_fields",
)

RUN_SCHEMA_VERSION: Final = 1
HISTORY_LINE_VERSION: Final = 1
DEFAULT_CONCURRENCY: Final = 4
RATE_DECIMALS: Final = 4
