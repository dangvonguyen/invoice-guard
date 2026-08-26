"""The extraction model's structured-output contract and client boundary."""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Protocol

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.llm import get_anthropic_client, get_openai_client


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

    def __init__(self, *, client: AsyncOpenAI, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        response = await self._client.responses.create(
            model=self._model,
            instructions=_EXTRACTION_INSTRUCTIONS,
            input=_build_messages(document_text, validation_error),
            max_output_tokens=self._max_tokens,
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


class AnthropicModelClient:
    """`ModelClient` backed by Anthropic."""

    def __init__(self, *, client: AsyncAnthropic, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        response = await self._client.messages.create(
            max_tokens=self._max_tokens,
            model=self._model,
            system=_EXTRACTION_INSTRUCTIONS,
            messages=_build_messages(document_text, validation_error),
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": OUTPUT_SCHEMA,
                }
            },
        )
        return json.loads(  # type: ignore[no-any-return]
            next(block.text for block in response.content if block.type == "text")
        )


def build_model_client(
    *, provider: Literal["openai", "anthropic"], model: str, max_tokens: int
) -> ModelClient:
    """Return the `ModelClient` for the configured extraction provider."""
    if provider == "openai":
        return OpenAIModelClient(
            client=get_openai_client(), model=model, max_tokens=max_tokens
        )
    else:
        return AnthropicModelClient(
            client=get_anthropic_client(), model=model, max_tokens=max_tokens
        )


def _build_messages(document_text: str, validation_error: str | None) -> list[Any]:
    content = f"Document text:\n\n{document_text}"
    if validation_error is not None:
        content += (
            f"\n\nYour previous response failed schema validation with this "
            f"error — correct it and respond again:\n{validation_error}"
        )
    return [{"role": "user", "content": content}]
