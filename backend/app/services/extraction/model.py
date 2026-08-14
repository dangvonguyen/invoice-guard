"""The extraction model's structured-output contract and client boundary."""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel


class ExtractedLineItem(BaseModel):
    """One line item on an invoice."""

    description: str
    amount: Decimal


class ExtractedInvoice(BaseModel):
    """Schema-constrained fields the extraction model must return."""

    vendor_name: str
    invoice_date: date
    total_amount: Decimal
    currency: str
    tax_amount: Decimal
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
        "invoice_date": {
            "type": "string",
            "description": "ISO 8601 date, e.g. 2000-01-01",
        },
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code, e.g. USD",
        },
        "tax_amount": {
            "type": "string",
            "description": "Decimal amount as a string, e.g. 32.10",
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
                    "amount": {"type": "string"},
                },
                "required": ["description", "amount"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "vendor_name",
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


class OpenAIModelClient:
    """`ModelClient` backed by OpenAI's structured outputs."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        response = await self._client.responses.create(
            model=self._model,
            instructions=_EXTRACTION_INSTRUCTIONS,
            input=self._build_user_input(document_text, validation_error),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "invoice_fields",
                    "schema": OUTPUT_SCHEMA,
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)  # type: ignore[no-any-return]

    @staticmethod
    def _build_user_input(document_text: str, validation_error: str | None) -> str:
        if validation_error is None:
            return f"Document text:\n\n{document_text}"
        return (
            f"Document text:\n\n{document_text}\n\n"
            "Your previous response failed schema validation with this "
            f"error — correct it and respond again:\n{validation_error}"
        )
