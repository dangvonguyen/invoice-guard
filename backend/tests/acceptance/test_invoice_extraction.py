"""Acceptance scenarios for invoice field extraction.

The extraction job has no HTTP entry point , so the acceptance boundary
for this feature is: invoke `extract_invoice` directly against real,
fully-wired collaborators (repository, storage, text extractor, grounding
checker), then observe the result over HTTP via `GET /invoices/{id}`.
The extraction *model* is the one collaborator faked here.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
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
from app.services.extraction import ExtractionService
from app.services.pdf_text_extractor import PdfTextExtractor
from app.services.span_grounding import SpanGroundingChecker
from app.workers.extract_invoice import extract_invoice

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

VENDOR_NAME = "Acme Supplies"
INVOICE_DATE = date(2000, 1, 1)
TOTAL_AMOUNT = Decimal("482.10")
TAX_AMOUNT = Decimal("32.10")
CURRENCY = "USD"


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


class FakeExtractionModelClient:
    """Stand in for the real LLM boundary with a fixed, schema-valid response."""

    async def extract(self, *, document_text: str) -> dict:
        assert VENDOR_NAME in document_text  # sanity: real text was passed in
        return {
            "vendor_name": VENDOR_NAME,
            "invoice_date": INVOICE_DATE.isoformat(),
            "total_amount": str(TOTAL_AMOUNT),
            "currency": CURRENCY,
            "tax_amount": str(TAX_AMOUNT),
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


async def should_extract_fields_from_a_text_native_pdf_on_first_valid_response(
    client: AsyncClient,
    test_db: AsyncSession,
    stored_invoice: tuple[Invoice, LocalStorageClient],
    auth_headers: dict[str, str],
) -> None:
    """Convert a text-native pending invoice into grounded structured fields."""
    invoice, storage = stored_invoice
    extraction_service = ExtractionService(
        model=FakeExtractionModelClient(),
        grounding_checker=SpanGroundingChecker(),
    )

    await extract_invoice(
        invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=storage,
        text_extractor=PdfTextExtractor(),
        extraction_service=extraction_service,
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
