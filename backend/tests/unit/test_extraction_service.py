"""Specify how extraction service coordinates the model and grounding checker."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.extraction_service import ExtractionService

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


@pytest.fixture
def model() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def grounding_checker() -> Mock:
    return Mock()


@pytest.fixture
def service(model: AsyncMock, grounding_checker: Mock) -> ExtractionService:
    return ExtractionService(model=model, grounding_checker=grounding_checker)


async def should_return_high_confidence_when_every_field_is_grounded(
    service: ExtractionService, model: AsyncMock, grounding_checker: Mock
) -> None:
    """A schema-valid, fully-grounded response is high confidence."""
    model.extract.return_value = VALID_RAW_RESPONSE
    grounding_checker.check.return_value = True

    result = await service.extract(document_text=DOCUMENT_TEXT)

    model.extract.assert_awaited_once_with(document_text=DOCUMENT_TEXT)
    assert result.fields.vendor_name == "Acme Supplies"
    assert str(result.fields.total_amount) == "482.10"
    assert result.confidence == "high"
    assert result.confidence_reason is None


async def should_check_every_extracted_field_against_the_source_text(
    service: ExtractionService, model: AsyncMock, grounding_checker: Mock
) -> None:
    """Ground each scalar field individually, not just the response as a whole."""
    model.extract.return_value = VALID_RAW_RESPONSE
    grounding_checker.check.return_value = True

    await service.extract(document_text=DOCUMENT_TEXT)

    checked_values = {
        call.kwargs["value"] for call in grounding_checker.check.call_args_list
    }
    assert "Acme Supplies" in checked_values
    assert "482.10" in checked_values
    for call in grounding_checker.check.call_args_list:
        assert call.kwargs["source_text"] == DOCUMENT_TEXT


async def should_flag_low_confidence_when_a_field_is_not_grounded(
    service: ExtractionService, model: AsyncMock, grounding_checker: Mock
) -> None:
    """A schema-valid but ungrounded field lowers confidence, not the field value."""
    model.extract.return_value = {**VALID_RAW_RESPONSE, "total_amount": "999.00"}

    def check(*, value: str, source_text: str) -> bool:
        del source_text
        return value != "999.00"

    grounding_checker.check.side_effect = check

    result = await service.extract(document_text=DOCUMENT_TEXT)

    assert str(result.fields.total_amount) == "999.00"
    assert result.confidence == "low"
    assert result.confidence_reason is not None
