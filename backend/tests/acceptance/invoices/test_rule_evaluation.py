"""Acceptance scenarios for deterministic rule evaluation.

Steps:
- Build a real PDF with `fpdf` containing example invoice values
- Store the PDF in a storage under `tmp_path`
- Run the extraction and rule-evaluation flow
- Verify the resulting invoice through the HTTP API
- Verify the complete persisted rule-result row in the database
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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
from app.database.models.rule_result import RuleOutcome
from app.database.models.user import User
from app.database.repositories.invoice import InvoiceRepository
from app.database.repositories.rule_result import RuleResultRepository
from app.queueing.jobs.evaluate_rules import evaluate_rules
from app.queueing.jobs.extract_invoice import extract_invoice
from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.text import PdfTextExtractor
from app.services.rules.config import RuleConfig
from app.services.rules.engine import RuleEngine
from app.services.rules.result import RuleCode

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]

RULE_CONFIG = RuleConfig(
    max_expense_amount=Decimal("1000.00"),
    max_expense_age_days=90,
    allowed_currencies=frozenset({"USD", "EUR", "GBP"}),
    reconciliation_tolerance=Decimal("0.01"),
)
TODAY = date(2026, 8, 15)

VENDOR_NAME = "Acme Supplies"
INVOICE_DATE = date(2026, 7, 30)
CURRENCY = "USD"
TAX_AMOUNT = Decimal("36.00")
TOTAL_AMOUNT = Decimal("486.00")
LINE_ITEMS = [
    ("Standing desk riser", Decimal("320.00")),
    ("Monitor arm", Decimal("130.00")),
]
EXTRACTED_FIELDS = {
    "vendor_name": VENDOR_NAME,
    "invoice_date": INVOICE_DATE.isoformat(),
    "currency": CURRENCY,
    "tax_amount": str(TAX_AMOUNT),
    "total_amount": str(TOTAL_AMOUNT),
    "line_items": [
        {"description": description, "amount": str(amount)}
        for description, amount in LINE_ITEMS
    ],
}


@dataclass(frozen=True)
class StoredInvoice:
    invoice: Invoice
    storage: LocalStorageClient


StoreInvoice = Callable[[bytes], Awaitable[StoredInvoice]]


def _pdf_bytes(text: str | None = None) -> bytes:
    """Build a real PDF, optionally with a text layer containing `text`."""
    pdf = FPDF()
    pdf.add_page()
    if text is not None:
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text=text)
    return bytes(pdf.output())


def compliant_invoice_pdf_bytes() -> bytes:
    """A real, parseable PDF containing a fully compliant invoice."""
    line_items_text = "\n".join(
        f"{description}: {amount} {CURRENCY}" for description, amount in LINE_ITEMS
    )
    return _pdf_bytes(
        f"Vendor: {VENDOR_NAME}\n"
        f"Invoice Date: {INVOICE_DATE.isoformat()}\n"
        f"{line_items_text}\n"
        f"Tax: {TAX_AMOUNT} {CURRENCY}\n"
        f"Total: {TOTAL_AMOUNT} {CURRENCY}\n"
    )


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the employee who owns the invoice being evaluated."""
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
async def store_invoice(
    test_db: AsyncSession, owner: User, tmp_path: Path
) -> StoreInvoice:
    """A helper that persists invoice content in local test storage."""
    storage = LocalStorageClient(base_path=tmp_path)
    repository = InvoiceRepository(session=test_db)

    async def store(content: bytes) -> StoredInvoice:
        invoice = await repository.create_pending(
            owner_id=owner.id,
            storage_key=storage.generate_key(),
            original_filename="invoice.pdf",
        )
        await storage.save(key=invoice.storage_key, content=content)
        return StoredInvoice(invoice=invoice, storage=storage)

    return store


class FakeExtractionModelClient:
    """Stand in for the real LLM boundary with a fixed, schema-valid response."""

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        assert VENDOR_NAME in document_text  # sanity check
        return EXTRACTED_FIELDS


async def extract_and_fetch(
    *,
    client: AsyncClient,
    test_db: AsyncSession,
    auth_headers: dict[str, str],
    stored: StoredInvoice,
    model: Any,
) -> dict[str, Any]:
    """Run extraction, then rule evaluation, and return the invoice exposed by the API."""
    extracted_invoice = await extract_invoice(
        stored.invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=stored.storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=ExtractionPipeline(
            model=model,
            grounding_checker=GroundingChecker(),
        ),
    )
    if extracted_invoice is not None:
        await evaluate_rules(
            stored.invoice.id,
            extracted_invoice=extracted_invoice,
            rule_results=RuleResultRepository(session=test_db),
            rule_engine=RuleEngine(config=RULE_CONFIG),
            today=TODAY,
        )
    await test_db.commit()

    response = await client.get(f"/invoices/{stored.invoice.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    return response.json()


async def should_record_all_check_pass_for_a_compliant_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    auth_headers: dict[str, str],
) -> None:
    """Evaluate every rule as `pass` for a fully compliant invoice."""
    stored = await store_invoice(compliant_invoice_pdf_bytes())

    body = await extract_and_fetch(
        client=client,
        test_db=test_db,
        auth_headers=auth_headers,
        stored=stored,
        model=FakeExtractionModelClient(),
    )

    assert body["status"] == "extracted"

    # Database-level rule code assertion
    rows = await RuleResultRepository(test_db).list_by_invoice(stored.invoice.id)
    assert {row.rule_code for row in rows} == {code.value for code in RuleCode}
    assert all(row.outcome == RuleOutcome.PASS for row in rows)
