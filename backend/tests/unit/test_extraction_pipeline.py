"""Specify how extraction service coordinates the model and grounding checker."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.extraction.pipeline import ExtractionPipeline, InvalidModelOutputError
from app.services.span_grounding import SpanGroundingChecker

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

DOCUMENT_TEXT = "Vendor: Acme Supplies\nTotal: 482.10 USD"
VALID_RAW_RESPONSE = {
    "vendor_name": "Acme Supplies",
    "invoice_date": "2026-08-03",
    "total_amount": "482.10",
    "currency": "USD",
    "tax_amount": "32.10",
    "line_items": [],
}
INVALID_RAW_RESPONSE = {
    "vendor_name": "Acme Supplies",
    "invoice_date": "2026-08-03",
    "currency": "USD",
    "tax_amount": "32.10",
    "line_items": [],
}  # missing total_amount


@pytest.fixture
def model() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def grounding_checker() -> Mock:
    return Mock()


@pytest.fixture
def pipeline(model: AsyncMock, grounding_checker: Mock) -> ExtractionPipeline:
    return ExtractionPipeline(model=model, grounding_checker=grounding_checker)


async def should_return_high_confidence_when_every_field_is_grounded(
    pipeline: ExtractionPipeline, model: AsyncMock, grounding_checker: Mock
) -> None:
    """A schema-valid, fully-grounded response is high confidence."""
    model.extract.return_value = VALID_RAW_RESPONSE
    grounding_checker.check.return_value = True

    result = await pipeline.run(document_text=DOCUMENT_TEXT)

    model.extract.assert_awaited_once_with(
        document_text=DOCUMENT_TEXT, validation_error=None
    )
    assert result.fields.vendor_name == "Acme Supplies"
    assert str(result.fields.total_amount) == "482.10"
    assert result.confidence == "high"
    assert result.confidence_reason is None


async def should_check_every_extracted_field_against_the_source_text(
    pipeline: ExtractionPipeline, model: AsyncMock, grounding_checker: Mock
) -> None:
    """Ground each scalar field individually, not just the response as a whole."""
    model.extract.return_value = VALID_RAW_RESPONSE
    grounding_checker.check.return_value = True

    await pipeline.run(document_text=DOCUMENT_TEXT)

    checked_values = {
        call.kwargs["value"] for call in grounding_checker.check.call_args_list
    }
    assert "Acme Supplies" in checked_values
    assert "482.10" in checked_values
    for call in grounding_checker.check.call_args_list:
        assert call.kwargs["source_text"] == DOCUMENT_TEXT


async def should_flag_low_confidence_when_a_field_is_not_grounded(
    pipeline: ExtractionPipeline, model: AsyncMock, grounding_checker: Mock
) -> None:
    """A schema-valid but ungrounded field lowers confidence, not the field value."""
    model.extract.return_value = {**VALID_RAW_RESPONSE, "total_amount": "999.00"}

    def check(*, value: str, source_text: str) -> bool:
        del source_text
        return value != "999.00"

    grounding_checker.check.side_effect = check

    result = await pipeline.run(document_text=DOCUMENT_TEXT)

    assert str(result.fields.total_amount) == "999.00"
    assert result.confidence == "low"
    assert result.confidence_reason is not None


async def should_ground_dates_and_amounts_using_equivalent_source_formats(
    model: AsyncMock,
) -> None:
    """Validated dates and decimals need not retain their source formatting."""
    model.extract.return_value = {
        **VALID_RAW_RESPONSE,
        "invoice_date": "2026-08-13",
        "total_amount": "1234.56",
    }
    pipeline = ExtractionPipeline(model=model, grounding_checker=SpanGroundingChecker())
    document_text = (
        "Vendor: Acme Supplies\nInvoice date: 08/13/2026\n"
        "Tax: 32.10 USD\nTotal: 1,234.56 USD"
    )

    result = await pipeline.run(document_text=document_text)

    assert result.confidence == "high"
    assert result.confidence_reason is None


async def should_not_ground_different_dates_or_grouped_amounts(
    model: AsyncMock,
) -> None:
    """Format-aware comparison must still reject unequal values."""
    model.extract.return_value = {
        **VALID_RAW_RESPONSE,
        "invoice_date": "2026-08-14",
        "total_amount": "1235.56",
    }
    pipeline = ExtractionPipeline(model=model, grounding_checker=SpanGroundingChecker())
    document_text = (
        "Vendor: Acme Supplies\nInvoice date: 08/13/2026\n"
        "Tax: 32.10 USD\nTotal: 1,234.56 USD"
    )

    result = await pipeline.run(document_text=document_text)

    assert result.confidence == "low"
    assert result.confidence_reason is not None
    assert "invoice_date" in result.confidence_reason
    assert "total_amount" in result.confidence_reason


async def should_ground_line_item_descriptions_and_formatted_amounts(
    model: AsyncMock,
) -> None:
    """Line-item fields participate in grounding with semantic amounts."""
    model.extract.return_value = {
        **VALID_RAW_RESPONSE,
        "line_items": [{"description": "Consulting", "amount": "1234.56"}],
    }
    pipeline = ExtractionPipeline(model=model, grounding_checker=SpanGroundingChecker())
    document_text = (
        "Vendor: Acme Supplies\nInvoice date: 2026-08-03\n"
        "Consulting 1,234.56\nTax: 32.10 USD\nTotal: 482.10 USD"
    )

    result = await pipeline.run(document_text=document_text)

    assert result.confidence == "high"
    assert result.confidence_reason is None


async def should_flag_ungrounded_line_item_fields_as_low_confidence(
    model: AsyncMock,
) -> None:
    """Fabricated line-item descriptions and amounts lower confidence."""
    model.extract.return_value = {
        **VALID_RAW_RESPONSE,
        "line_items": [{"description": "Fabricated service", "amount": "999.00"}],
    }
    pipeline = ExtractionPipeline(model=model, grounding_checker=SpanGroundingChecker())
    document_text = (
        "Vendor: Acme Supplies\nInvoice date: 2026-08-03\n"
        "Consulting 100.00\nTax: 32.10 USD\nTotal: 482.10 USD"
    )

    result = await pipeline.run(document_text=document_text)

    assert result.confidence == "low"
    assert result.confidence_reason is not None
    assert "line_items[0].description" in result.confidence_reason
    assert "line_items[0].amount" in result.confidence_reason


async def should_retry_and_succeed_when_a_later_attempt_is_schema_valid(
    pipeline: ExtractionPipeline, model: AsyncMock, grounding_checker: Mock
) -> None:
    """A schema-invalid first attempt is retried, not fatal, within budget."""
    model.extract.side_effect = [INVALID_RAW_RESPONSE, VALID_RAW_RESPONSE]
    grounding_checker.check.return_value = True

    result = await pipeline.run(document_text=DOCUMENT_TEXT)

    assert model.extract.await_count == 2
    assert str(result.fields.total_amount) == "482.10"
    assert result.confidence == "high"


async def should_reprompt_with_the_previous_validation_error_on_retry(
    pipeline: ExtractionPipeline, model: AsyncMock, grounding_checker: Mock
) -> None:
    """Feed the prior attempt's schema-validation failure back to the model."""
    model.extract.side_effect = [INVALID_RAW_RESPONSE, VALID_RAW_RESPONSE]
    grounding_checker.check.return_value = True

    await pipeline.run(document_text=DOCUMENT_TEXT)

    first_call, second_call = model.extract.await_args_list
    assert first_call.kwargs["validation_error"] is None
    assert second_call.kwargs["validation_error"] is not None
    assert "total_amount" in second_call.kwargs["validation_error"]


async def should_raise_after_exhausting_all_retry_attempts(
    pipeline: ExtractionPipeline, model: AsyncMock, grounding_checker: Mock
) -> None:
    """Give up after 1 initial attempt plus 2 retries, all schema-invalid."""
    model.extract.return_value = INVALID_RAW_RESPONSE
    grounding_checker.check.return_value = True

    with pytest.raises(InvalidModelOutputError):
        await pipeline.run(document_text=DOCUMENT_TEXT)

    assert model.extract.await_count == 3
