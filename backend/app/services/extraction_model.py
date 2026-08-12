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

    async def extract(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        """Return the model's raw structured response for one document.

        Args:
            validation_error: carries the previous attempt's schema-validation
            failure back to the model so it can be re-prompted; `None` on the
            first attempt.
        """
        ...


class TempExtractionModelClient:
    """Temporary `ExtractionModelClient` until an LLM vendor is chosen."""

    async def extract(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError()
