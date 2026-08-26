"""Specify how the OpenAI extraction model client builds requests and parses replies."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.extraction.model import OUTPUT_SCHEMA, OpenAIModelClient
from tests.support.constants import RAW_INVOICE_DATA

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

DOCUMENT_TEXT = "Vendor: Acme Supplies\nTotal: 482.10 USD"


@pytest.fixture
def openai_client() -> Mock:
    client = Mock()
    client.responses.create = AsyncMock(
        return_value=Mock(output_text=json.dumps(RAW_INVOICE_DATA))
    )
    return client


@pytest.fixture
def model_client(openai_client: Mock) -> OpenAIModelClient:
    return OpenAIModelClient(client=openai_client, model="gpt-5-mini", max_tokens=4096)


async def should_return_the_parsed_json_response(
    model_client: OpenAIModelClient,
) -> None:
    """Parse the model's output_text into the raw field dict."""
    result = await model_client.extract_raw_fields(document_text=DOCUMENT_TEXT)

    assert result == RAW_INVOICE_DATA


async def should_request_a_strict_json_schema_matching_invoice_fields(
    model_client: OpenAIModelClient, openai_client: Mock
) -> None:
    """Enforce the response shape via a strict Structured Outputs schema."""
    await model_client.extract_raw_fields(document_text=DOCUMENT_TEXT)

    _, kwargs = openai_client.responses.create.call_args
    response_format = kwargs["text"]["format"]
    assert response_format["schema"] == OUTPUT_SCHEMA
    assert response_format["strict"] is True


async def should_include_the_document_text_in_the_first_attempt(
    model_client: OpenAIModelClient, openai_client: Mock
) -> None:
    """Send the source document text on attempt one."""
    await model_client.extract_raw_fields(document_text=DOCUMENT_TEXT)

    _, kwargs = openai_client.responses.create.call_args
    assert DOCUMENT_TEXT in kwargs["input"][0]["content"]


async def should_include_the_prior_validation_error_when_retrying(
    model_client: OpenAIModelClient, openai_client: Mock
) -> None:
    """Re-prompt with the previous attempt's schema-validation failure."""
    await model_client.extract_raw_fields(
        document_text=DOCUMENT_TEXT, validation_error="total_amount: field required"
    )

    _, kwargs = openai_client.responses.create.call_args
    assert DOCUMENT_TEXT in kwargs["input"][0]["content"]
    assert "total_amount: field required" in kwargs["input"][0]["content"]
