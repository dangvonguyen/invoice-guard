"""Coordinate the extraction model and span-grounding checks."""

from dataclasses import dataclass
from typing import Literal

from app.services.extraction_model import ExtractionModelClient, InvoiceFields
from app.services.span_grounding import SpanGroundingChecker


@dataclass(frozen=True)
class ExtractionResult:
    """One extraction attempt's persisted-worthy outcome."""

    fields: InvoiceFields
    confidence: Literal["high", "low"]
    confidence_reason: str | None


class ExtractionService:
    """Convert invoice text into schema-validated structured fields."""

    _GROUNDED_FIELD_NAMES = (
        "vendor_name",
        "invoice_date",
        "total_amount",
        "tax_amount",
        "currency",
    )

    def __init__(
        self, model: ExtractionModelClient, grounding_checker: SpanGroundingChecker
    ) -> None:
        self._model = model
        self._grounding_checker = grounding_checker

    async def extract(self, *, document_text: str) -> ExtractionResult:
        """Return structured invoice fields extracted from document text."""
        raw_response = await self._model.extract(document_text=document_text)
        fields = InvoiceFields.model_validate(raw_response)

        ungrounded = self._ungrounded_field_names(fields, document_text)
        if not ungrounded:
            return ExtractionResult(
                fields=fields, confidence="high", confidence_reason=None
            )

        reason = f"not found in source text: {', '.join(ungrounded)}"
        return ExtractionResult(
            fields=fields, confidence="low", confidence_reason=reason
        )

    def _ungrounded_field_names(
        self, fields: InvoiceFields, document_text: str
    ) -> list[str]:
        ungrounded: list[str] = []
        for field_name in self._GROUNDED_FIELD_NAMES:
            value = str(getattr(fields, field_name))
            if not self._grounding_checker.check(
                value=value, source_text=document_text
            ):
                ungrounded.append(field_name)
        return ungrounded
