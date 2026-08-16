"""Acceptance scenarios for invoice field extraction.

The extraction job has no HTTP entry point, so the acceptance boundary
for this feature is: invoke `extract_invoice` directly against real,
fully-wired collaborators (repository, storage, text extractor, grounding
checker), then observe the result over HTTP via `GET /invoices/{id}`.
The extraction *model* is the one collaborator faked here.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorageClient
from app.database.models.invoice import Invoice
from app.database.models.user import User
from app.database.repositories.invoice import InvoiceRepository
from app.queueing.jobs.extract_invoice import extract_invoice
from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.text import PdfTextExtractor
from tests.support.constants import (
    CURRENCY,
    INVOICE_DATE,
    LINE_ITEMS,
    RAW_INVOICE_DATA,
    TAX_AMOUNT,
    TOTAL_AMOUNT,
    VENDOR_NAME,
)
from tests.support.pdf import pdf_bytes

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


@dataclass(frozen=True)
class StoredInvoice:
    invoice: Invoice
    storage: LocalStorageClient


StoreInvoice = Callable[[bytes], Awaitable[StoredInvoice]]


@pytest_asyncio.fixture
async def store_invoice(
    test_db: AsyncSession, employee: User, tmp_path: Path
) -> StoreInvoice:
    """A helper that persists invoice content in local test storage."""
    storage = LocalStorageClient(base_path=tmp_path)
    repository = InvoiceRepository(session=test_db)

    async def store(content: bytes) -> StoredInvoice:
        invoice = await repository.create_pending(
            owner_id=employee.id,
            storage_key=storage.generate_key(),
            original_filename="invoice.pdf",
        )
        await storage.save(key=invoice.storage_key, content=content)
        return StoredInvoice(invoice=invoice, storage=storage)

    return store


async def run_extraction(
    stored: StoredInvoice,
    *,
    test_db: AsyncSession,
    extraction_pipeline: ExtractionPipeline,
) -> None:
    """Run the extraction job against a stored invoice and commit the result."""
    await extract_invoice(
        stored.invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=stored.storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=extraction_pipeline,
    )
    await test_db.commit()


def text_native_pdf_bytes() -> bytes:
    """Build a real, parseable PDF containing the invoice's field values."""
    line_items_text = "\n".join(
        f"{description}: {amount} {CURRENCY}" for description, amount in LINE_ITEMS
    )
    return pdf_bytes(
        f"Vendor: {VENDOR_NAME}\n"
        f"Invoice Date: {INVOICE_DATE.isoformat()}\n"
        f"{line_items_text}\n"
        f"Tax: {TAX_AMOUNT} {CURRENCY}\n"
        f"Total: {TOTAL_AMOUNT} {CURRENCY}\n"
    )


def image_only_pdf_bytes() -> bytes:
    """Build a real PDF page with no text layer (e.g. a scanned image)."""
    return pdf_bytes()


def text_native_pdf_bytes_with_ungrounded_amount() -> bytes:
    """Build a PDF with a grounded amount but not the ungrounded one."""
    return pdf_bytes(
        f"Vendor: {VENDOR_NAME}\n"
        f"Invoice Date: {INVOICE_DATE.isoformat()}\n"
        f"Tax: {TAX_AMOUNT} {CURRENCY}\n"
        f"Total: $120.00 {CURRENCY}\n"  # grounded amount
    )


class FakeExtractionModelClient:
    """Stand in for the real LLM boundary with a fixed, schema-valid response."""

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        assert VENDOR_NAME in document_text  # sanity: real text was passed in
        return RAW_INVOICE_DATA


class NeverCalledExtractionModelClient:
    """Stand in for the LLM boundary that must never be reached for this scenario."""

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        raise AssertionError(
            "extraction model should not be called when the PDF has no text layer"
        )


class AlwaysInvalidExtractionModelClient:
    """Stand in for an LLM boundary that never returns a schema-valid response."""

    def __init__(self) -> None:
        self.call_count = 0

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        del document_text, validation_error
        self.call_count += 1
        return {k: v for k, v in RAW_INVOICE_DATA.items() if k != "total_amount"}


class UngroundedFieldExtractionModelClient:
    """Stand in for an LLM returning a schema-valid value not in the source text."""

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        assert "$120.00" in document_text  # sanity: grounded value is present
        assert "$999.00" not in document_text  # sanity: ungrounded value is absent
        return {
            "vendor_name": VENDOR_NAME,
            "invoice_date": INVOICE_DATE.isoformat(),
            "currency": CURRENCY,
            "tax_amount": str(TAX_AMOUNT),
            "total_amount": "999.00",  # schema-valid, but ungrounded in source
            "line_items": [],
        }


async def should_extract_fields_from_a_text_native_pdf_on_first_valid_response(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Convert a text-native pending invoice into grounded structured fields."""
    stored = await store_invoice(text_native_pdf_bytes())
    await run_extraction(
        stored,
        test_db=test_db,
        extraction_pipeline=ExtractionPipeline(
            model=FakeExtractionModelClient(), grounding_checker=GroundingChecker()
        ),
    )

    response = await client.get(
        f"/invoices/{stored.invoice.id}", headers=employee_headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extracted"
    assert body["extracted_fields"]["vendor_name"] == VENDOR_NAME
    assert body["extracted_fields"]["total_amount"] == str(TOTAL_AMOUNT)
    assert body["extracted_fields"]["currency"] == CURRENCY
    assert body["confidence"] == "high"


async def should_fail_fast_for_a_pdf_without_a_text_layer(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Route a scanned/image-only PDF to extraction_failed with no model call."""
    stored = await store_invoice(image_only_pdf_bytes())
    await run_extraction(
        stored,
        test_db=test_db,
        extraction_pipeline=ExtractionPipeline(
            model=NeverCalledExtractionModelClient(),
            grounding_checker=GroundingChecker(),
        ),
    )

    response = await client.get(
        f"/invoices/{stored.invoice.id}", headers=employee_headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extraction_failed"


async def should_route_to_review_after_exhausting_validation_retries(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Fail extraction when the model never returns a schema-valid response."""
    stored = await store_invoice(text_native_pdf_bytes())
    model = AlwaysInvalidExtractionModelClient()
    await run_extraction(
        stored,
        test_db=test_db,
        extraction_pipeline=ExtractionPipeline(
            model=model, grounding_checker=GroundingChecker()
        ),
    )

    response = await client.get(
        f"/invoices/{stored.invoice.id}", headers=employee_headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extraction_failed"
    assert body["extracted_fields"] is None
    assert model.call_count == 3


async def should_flag_ungrounded_field_as_low_confidence(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Flag a schema-valid but ungrounded field value with low confidence."""
    stored = await store_invoice(text_native_pdf_bytes_with_ungrounded_amount())
    await run_extraction(
        stored,
        test_db=test_db,
        extraction_pipeline=ExtractionPipeline(
            model=UngroundedFieldExtractionModelClient(),
            grounding_checker=GroundingChecker(),
        ),
    )

    response = await client.get(
        f"/invoices/{stored.invoice.id}", headers=employee_headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extracted"
    assert body["extracted_fields"]["total_amount"] == "999.00"  # persisted as-is
    assert body["confidence"] == "low"
    assert "total_amount" in body["confidence_reason"]
