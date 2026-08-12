"""The extraction model's structured-output contract and client boundary."""

from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel


class LineItem(BaseModel):
    """One line item on an invoice."""

    description: str
    amount: Decimal


class InvoiceFields(BaseModel):
    """Schema-constrained fields the extraction model must return."""

    vendor_name: str
    invoice_date: date
    total_amount: Decimal
    currency: str
    tax_amount: Decimal
    line_items: list[LineItem] = []


class ExtractionModelClient(Protocol):
    """Call the extraction model and return its raw structured response."""

    async def extract(self, *, document_text: str) -> dict[str, Any]:
        """Return the model's raw structured response for one document."""
        ...
