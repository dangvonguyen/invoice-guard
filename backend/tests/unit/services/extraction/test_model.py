"""Specify how the extraction model client builds prompts and parses replies."""

import json
from unittest.mock import AsyncMock

import pytest

from app.services.extraction.model import OUTPUT_SCHEMA, LLMModelClient
from tests.support.constants import RAW_INVOICE_DATA

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

DOCUMENT_TEXT = "Vendor: Acme Supplies\nTotal: 482.10 USD"


@pytest.fixture
def llm() -> AsyncMock:
    llm = AsyncMock()
    llm.complete_json.return_value = json.dumps(RAW_INVOICE_DATA)
    return llm


@pytest.fixture
def model_client(llm: AsyncMock) -> LLMModelClient:
    return LLMModelClient(llm=llm)


async def should_return_the_parsed_json_response(
    model_client: LLMModelClient,
) -> None:
    """Parse the model's JSON text into the raw field dict."""
    result = await model_client.extract_raw_fields(document_text=DOCUMENT_TEXT)

    assert result == RAW_INVOICE_DATA


async def should_request_the_invoice_fields_schema(
    model_client: LLMModelClient, llm: AsyncMock
) -> None:
    """Constrain the response to the invoice-fields output schema."""
    await model_client.extract_raw_fields(document_text=DOCUMENT_TEXT)

    _, kwargs = llm.complete_json.call_args
    assert kwargs["schema"] == OUTPUT_SCHEMA


async def should_include_the_document_text_in_the_first_attempt(
    model_client: LLMModelClient, llm: AsyncMock
) -> None:
    """Send the source document text on attempt one."""
    await model_client.extract_raw_fields(document_text=DOCUMENT_TEXT)

    _, kwargs = llm.complete_json.call_args
    assert DOCUMENT_TEXT in kwargs["user_message"]


async def should_include_the_prior_validation_error_when_retrying(
    model_client: LLMModelClient, llm: AsyncMock
) -> None:
    """Re-prompt with the previous attempt's schema-validation failure."""
    await model_client.extract_raw_fields(
        document_text=DOCUMENT_TEXT, validation_error="total_amount: field required"
    )

    _, kwargs = llm.complete_json.call_args
    assert DOCUMENT_TEXT in kwargs["user_message"]
    assert "total_amount: field required" in kwargs["user_message"]
