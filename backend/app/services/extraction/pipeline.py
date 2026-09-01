"""Coordinate the extraction model and span-grounding checks."""

from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.model import ExtractedInvoice, ModelClient


@dataclass(frozen=True)
class ExtractionResult:
    """One extraction attempt's persisted-worthy outcome."""

    fields: ExtractedInvoice
    confidence: Literal["high", "low"]
    confidence_reason: str | None


class InvalidModelOutputError(Exception):
    """Raised when the model never returns a schema-valid response in budget."""


class ExtractionPipeline:
    """Convert invoice text into schema-validated structured fields."""

    _REQUIRING_FIELDS = (
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "total_amount",
        "tax_amount",
        "currency",
    )

    _MAX_MODEL_ATTEMPTS = 3

    def __init__(self, model: ModelClient, grounding_checker: GroundingChecker) -> None:
        self._model = model
        self._grounding_checker = grounding_checker

    async def run(self, *, document_text: str) -> ExtractionResult:
        """Return structured invoice fields extracted from document text.

        Raises:
            ExtractionValidationError: the model returned a schema-invalid
                response on every attempt, including retries.
        """
        validation_error: str | None = None
        for _ in range(self._MAX_MODEL_ATTEMPTS):
            raw_response = await self._model.extract_raw_fields(
                document_text=document_text, validation_error=validation_error
            )
            try:
                fields = ExtractedInvoice.model_validate(raw_response)
            except ValidationError as exc:
                validation_error = str(exc)
                continue
            return self._build_result(fields, document_text)

        raise InvalidModelOutputError(
            "model did not return a schema-valid response within "
            f"{self._MAX_MODEL_ATTEMPTS} attempts"
        )

    def _build_result(
        self, fields: ExtractedInvoice, document_text: str
    ) -> ExtractionResult:
        ungrounded = self._find_ungrounded_fields(fields, document_text)
        if not ungrounded:
            return ExtractionResult(
                fields=fields, confidence="high", confidence_reason=None
            )

        reason = f"not found in source text: {', '.join(ungrounded)}"
        return ExtractionResult(
            fields=fields, confidence="low", confidence_reason=reason
        )

    def _find_ungrounded_fields(
        self, fields: ExtractedInvoice, document_text: str
    ) -> list[str]:
        ungrounded: list[str] = []
        for field_name in self._REQUIRING_FIELDS:
            value = getattr(fields, field_name)
            if value is None:
                continue
            if not self._grounding_checker.is_grounded(
                value=value, source_text=document_text
            ):
                ungrounded.append(field_name)

        for index, line_item in enumerate(fields.line_items):
            if not self._grounding_checker.is_grounded(
                value=line_item.description, source_text=document_text
            ):
                ungrounded.append(f"line_items[{index}].description")
            if not self._grounding_checker.is_grounded(
                value=line_item.amount, source_text=document_text
            ):
                ungrounded.append(f"line_items[{index}].amount")
            if (
                line_item.quantity is not None
                and not self._grounding_checker.is_grounded(
                    value=line_item.quantity, source_text=document_text
                )
            ):
                ungrounded.append(f"line_items[{index}].quantity")
            if (
                line_item.unit_price is not None
                and not self._grounding_checker.is_grounded(
                    value=line_item.unit_price, source_text=document_text
                )
            ):
                ungrounded.append(f"line_items[{index}].unit_price")

        return ungrounded
