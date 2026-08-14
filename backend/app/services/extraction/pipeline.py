"""Coordinate the extraction model and span-grounding checks."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import ValidationError

from app.services.extraction.model import ExtractedInvoice, ModelClient
from app.services.span_grounding import SpanGroundingChecker


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
        "invoice_date",
        "total_amount",
        "tax_amount",
        "currency",
    )

    _MAX_MODEL_ATTEMPTS = 3

    def __init__(
        self, model: ModelClient, grounding_checker: SpanGroundingChecker
    ) -> None:
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
            if not self._is_grounded(value, document_text):
                ungrounded.append(field_name)

        for index, line_item in enumerate(fields.line_items):
            if not self._is_grounded(line_item.description, document_text):
                ungrounded.append(f"line_items[{index}].description")
            if not self._is_grounded(line_item.amount, document_text):
                ungrounded.append(f"line_items[{index}].amount")

        return ungrounded

    def _is_grounded(self, value: str | date | Decimal, document_text: str) -> bool:
        return any(
            self._grounding_checker.check(value=candidate, source_text=document_text)
            for candidate in self._grounding_candidates(value)
        )

    @staticmethod
    def _grounding_candidates(value: str | date | Decimal) -> tuple[str, ...]:
        """Return common source spellings equivalent to a validated value."""
        candidates: tuple[str, ...]
        if isinstance(value, date):
            year, month, day = value.year, value.month, value.day
            candidates = (
                f"{year:04d}-{month:02d}-{day:02d}",
                f"{month:02d}/{day:02d}/{year:04d}",
                f"{month}/{day}/{year:04d}",
                f"{day:02d}/{month:02d}/{year:04d}",
                f"{day}/{month}/{year:04d}",
            )
        elif isinstance(value, Decimal):
            candidates = (
                format(value, "f"),
                format(value, ",f"),
            )
        else:
            candidates = (value,)

        return tuple(dict.fromkeys(candidates))
