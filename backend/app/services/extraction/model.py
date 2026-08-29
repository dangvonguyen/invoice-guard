"""The extraction model's structured-output contract and client boundary."""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.config import ModelProvider
from app.core.llm import StructuredLLM, build_structured_llm


class ExtractedLineItem(BaseModel):
    """One line item on an invoice."""

    description: str
    amount: Decimal
    quantity: Decimal | None = None
    unit_price: Decimal | None = None


class ExtractedInvoice(BaseModel):
    """Schema-constrained fields the extraction model must return."""

    vendor_name: str
    invoice_number: str | None = None
    invoice_date: date
    total_amount: Decimal
    currency: str
    tax_amount: Decimal | None = None
    line_items: list[ExtractedLineItem] = []


class ModelClient(Protocol):
    """Call the extraction model and return its raw structured response."""

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        """Return the model's raw structured response for one document.

        Args:
            validation_error: carries the previous attempt's schema-validation
            failure back to the model so it can be re-prompted; `None` on the
            first attempt.
        """
        ...


OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string"},
        "invoice_number": {
            "type": ["string", "null"],
            "description": "Invoice number, if printed on the document",
        },
        "invoice_date": {
            "type": "string",
            "description": "ISO 8601 date, e.g. 2000-01-01",
        },
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code, e.g. USD",
        },
        "tax_amount": {
            "type": ["string", "null"],
            "description": (
                "Decimal tax amount as a string, e.g. 32.10. Use null when the "
                'document states no tax at all; use "0.00" only when a zero tax '
                "line is literally printed."
            ),
        },
        "total_amount": {
            "type": "string",
            "description": "Decimal amount as a string, e.g. 482.10",
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "amount": {
                        "type": "string",
                        "description": (
                            "Decimal line amount as a string, e.g. 37.50. If a line "
                            "shows both a pre-tax and a tax-inclusive amount, use the "
                            "pre-tax one."
                        ),
                    },
                    "quantity": {
                        "type": ["string", "null"],
                        "description": (
                            "Decimal quantity as a string, e.g. 3, taken from a "
                            "dedicated column or field; null if absent."
                        ),
                    },
                    "unit_price": {
                        "type": ["string", "null"],
                        "description": (
                            "Decimal unit price as a string, e.g. 12.50, taken from a "
                            "dedicated column or field; null if absent."
                        ),
                    },
                },
                "required": ["description", "amount", "quantity", "unit_price"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "total_amount",
        "currency",
        "tax_amount",
        "line_items",
    ],
    "additionalProperties": False,
}

_EXTRACTION_INSTRUCTIONS = (
    "Extract invoice fields from the document text the user provides. "
    "Only report values that literally appear in the text; never invent or "
    "estimate a value that isn't present."
)


class LLMModelClient:
    """`ModelClient` backed by a structured-output LLM."""

    def __init__(self, *, llm: StructuredLLM) -> None:
        self._llm = llm

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        raw = await self._llm.complete_json(
            instructions=_EXTRACTION_INSTRUCTIONS,
            schema=OUTPUT_SCHEMA,
            schema_name="invoice_fields",
            user_message=_build_prompt(document_text, validation_error),
        )
        return json.loads(raw)  # type: ignore[no-any-return]


def build_model_client(
    *, provider: ModelProvider, model: str, max_tokens: int
) -> ModelClient:
    """Return the `ModelClient` for the configured extraction provider."""
    return LLMModelClient(
        llm=build_structured_llm(provider=provider, model=model, max_tokens=max_tokens)
    )


def _build_prompt(document_text: str, validation_error: str | None) -> str:
    content = f"Document text:\n\n{document_text}"
    if validation_error is not None:
        content += (
            f"\n\nYour previous response failed schema validation with this "
            f"error — correct it and respond again:\n{validation_error}"
        )
    return content
