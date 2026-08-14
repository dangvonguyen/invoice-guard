"""Acceptance scenarios for invoice field extraction.

The extraction job has no HTTP entry point, so the acceptance boundary
for this feature is: invoke `extract_invoice` directly against real,
fully-wired collaborators (repository, storage, text extractor, grounding
checker), then observe the result over HTTP via `GET /invoices/{id}`.
The extraction *model* is the one collaborator faked here.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import status
from fpdf import FPDF
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_access_token_codec
from app.core.storage import LocalStorageClient
from app.database.models.invoice import Invoice
from app.database.models.user import User
from app.database.repositories.invoice import InvoiceRepository
from app.jobs.extract_invoice import extract_invoice
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.span_grounding import SpanGroundingChecker
from app.services.text_extractor import PdfTextExtractor

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

VENDOR_NAME = "Acme Supplies"
INVOICE_DATE = date(2000, 1, 1)
TOTAL_AMOUNT = Decimal("482.10")
TAX_AMOUNT = Decimal("32.10")
CURRENCY = "USD"
EXTRACTED_FIELDS = {
    "vendor_name": VENDOR_NAME,
    "invoice_date": INVOICE_DATE.isoformat(),
    "currency": CURRENCY,
    "tax_amount": str(TAX_AMOUNT),
    "total_amount": str(TOTAL_AMOUNT),
    "line_items": [],
}


def text_native_pdf_bytes() -> bytes:
    """Build a real, parseable PDF containing the invoice's field values."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0,
        10,
        text=(
            f"Vendor: {VENDOR_NAME}\n"
            f"Invoice Date: {INVOICE_DATE.isoformat()}\n"
            f"Tax: {TAX_AMOUNT} {CURRENCY}\n"
            f"Total: {TOTAL_AMOUNT} {CURRENCY}\n"
        ),
    )
    return bytes(pdf.output())


def image_only_pdf_bytes() -> bytes:
    """Build a real PDF page with no text layer (e.g. a scanned image)."""
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())


def text_native_pdf_bytes_with_ungrounded_amount() -> bytes:
    """Build a PDF with a grounded amount but not the ungrounded one."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0,
        10,
        text=(
            f"Vendor: {VENDOR_NAME}\n"
            f"Invoice Date: {INVOICE_DATE.isoformat()}\n"
            f"Tax: {TAX_AMOUNT} {CURRENCY}\n"
            f"Total: $120.00 {CURRENCY}\n"  # grounded amount
        ),
    )
    return bytes(pdf.output())


class FakeExtractionModelClient:
    """Stand in for the real LLM boundary with a fixed, schema-valid response."""

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        assert VENDOR_NAME in document_text  # sanity: real text was passed in
        return EXTRACTED_FIELDS


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
        return {k: v for k, v in EXTRACTED_FIELDS.items() if k != "total_amount"}


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


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the employee who owns the invoice being extracted."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="alice@example.com",
        hashed_password="unused-password-hash",
        name="Alice",
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def auth_headers(owner: User) -> dict[str, str]:
    """Bearer header authenticating as the invoice's owner."""
    token = get_access_token_codec().issue(str(owner.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def stored_invoice(
    test_db: AsyncSession, owner: User, tmp_path: Path
) -> tuple[Invoice, LocalStorageClient]:
    """Reserve a pending invoice and write its real PDF bytes to storage."""
    storage = LocalStorageClient(base_path=tmp_path)
    repository = InvoiceRepository(session=test_db)
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key=storage.generate_key(),
        original_filename="invoice.pdf",
    )
    await storage.save(key=invoice.storage_key, content=text_native_pdf_bytes())
    return invoice, storage


@pytest_asyncio.fixture
async def stored_invoice_without_text_layer(
    test_db: AsyncSession, owner: User, tmp_path: Path
) -> tuple[Invoice, LocalStorageClient]:
    """Reserve a pending invoice whose stored PDF has no extractable text."""
    storage = LocalStorageClient(base_path=tmp_path)
    repository = InvoiceRepository(session=test_db)
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key=storage.generate_key(),
        original_filename="invoice.pdf",
    )
    await storage.save(key=invoice.storage_key, content=image_only_pdf_bytes())
    return invoice, storage


@pytest_asyncio.fixture
async def stored_invoice_with_ungrounded_amount(
    test_db: AsyncSession, owner: User, tmp_path: Path
) -> tuple[Invoice, LocalStorageClient]:
    """Reserve a pending invoice with an extracted value not grounded in the PDF."""
    storage = LocalStorageClient(base_path=tmp_path)
    repository = InvoiceRepository(session=test_db)
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key=storage.generate_key(),
        original_filename="invoice.pdf",
    )
    await storage.save(
        key=invoice.storage_key, content=text_native_pdf_bytes_with_ungrounded_amount()
    )
    return invoice, storage


async def should_extract_fields_from_a_text_native_pdf_on_first_valid_response(
    client: AsyncClient,
    test_db: AsyncSession,
    stored_invoice: tuple[Invoice, LocalStorageClient],
    auth_headers: dict[str, str],
) -> None:
    """Convert a text-native pending invoice into grounded structured fields."""
    invoice, storage = stored_invoice
    extraction_pipeline = ExtractionPipeline(
        model=FakeExtractionModelClient(),
        grounding_checker=SpanGroundingChecker(),
    )

    await extract_invoice(
        invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=extraction_pipeline,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=auth_headers)

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
    stored_invoice_without_text_layer: tuple[Invoice, LocalStorageClient],
    auth_headers: dict[str, str],
) -> None:
    """Route a scanned/image-only PDF to extraction_failed with no model call."""
    invoice, storage = stored_invoice_without_text_layer
    extraction_pipeline = ExtractionPipeline(
        model=NeverCalledExtractionModelClient(),
        grounding_checker=SpanGroundingChecker(),
    )

    await extract_invoice(
        invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=extraction_pipeline,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extraction_failed"


async def should_route_to_review_after_exhausting_validation_retries(
    client: AsyncClient,
    test_db: AsyncSession,
    stored_invoice: tuple[Invoice, LocalStorageClient],
    auth_headers: dict[str, str],
) -> None:
    """Fail extraction when the model never returns a schema-valid response."""
    invoice, storage = stored_invoice
    model = AlwaysInvalidExtractionModelClient()
    extraction_pipeline = ExtractionPipeline(
        model=model,
        grounding_checker=SpanGroundingChecker(),
    )

    await extract_invoice(
        invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=extraction_pipeline,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extraction_failed"
    assert body["extracted_fields"] is None
    assert model.call_count == 3


async def should_flag_ungrounded_field_as_low_confidence(
    client: AsyncClient,
    test_db: AsyncSession,
    stored_invoice_with_ungrounded_amount: tuple[Invoice, LocalStorageClient],
    auth_headers: dict[str, str],
) -> None:
    """Flag a schema-valid but ungrounded field value with low confidence."""
    invoice, storage = stored_invoice_with_ungrounded_amount
    extraction_pipeline = ExtractionPipeline(
        model=UngroundedFieldExtractionModelClient(),
        grounding_checker=SpanGroundingChecker(),
    )

    await extract_invoice(
        invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=extraction_pipeline,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "extracted"
    assert body["extracted_fields"]["total_amount"] == "999.00"  # persisted as-is
    assert body["confidence"] == "low"
    assert "total_amount" in body["confidence_reason"]
