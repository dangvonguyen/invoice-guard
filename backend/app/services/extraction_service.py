"""Coordinate the extraction model and span-grounding checks."""

from dataclasses import dataclass
from typing import Literal

from app.services.extraction_model import InvoiceFields


@dataclass(frozen=True)
class ExtractionResult:
    """One extraction attempt's persisted-worthy outcome."""

    fields: InvoiceFields
    confidence: Literal["high", "low"]
    confidence_reason: str | None


class ExtractionService:
    """Convert invoice text into schema-validated structured fields."""

    async def extract(self, *, document_text: str) -> ExtractionResult:
        """Return structured invoice fields extracted from document text."""
        ...
