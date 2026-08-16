"""Acceptance scenarios for deterministic rule evaluation.

Steps:
- Build a real PDF with `fpdf` containing example invoice values
- Store the PDF in a storage under `tmp_path`
- Run the extraction and rule-evaluation flow
- Verify the resulting invoice through the HTTP API
- Verify the complete persisted rule-result row in the database
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorageClient
from app.database.models.invoice import Invoice
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
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
from tests.support.pdf import pdf_bytes

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


def invoice_pdf_bytes(fields: dict[str, Any] | None = None) -> bytes:
    """Build a real text-layer PDF."""
    if fields is None:
        return pdf_bytes()

    line_items_text = "\n".join(
        f"{description}: {amount} {fields['currency']}"
        for description, amount in LINE_ITEMS
    )
    return pdf_bytes(
        f"Vendor: {fields['vendor_name']}\n"
        f"Invoice Date: {fields['invoice_date']}\n"
        f"{line_items_text}\n"
        f"Tax: {fields['tax_amount']} {fields['currency']}\n"
        f"Total: {fields['total_amount']} {fields['currency']}\n"
    )


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


class FakeExtractionModelClient:
    """Stand in for the real LLM boundary with a fixed, schema-valid response."""

    def __init__(self, fields: dict[str, Any] = EXTRACTED_FIELDS) -> None:
        self.fields = fields

    async def extract_raw_fields(
        self, *, document_text: str, validation_error: str | None = None
    ) -> dict[str, Any]:
        assert self.fields["vendor_name"] in document_text  # sanity check
        return self.fields


async def extract_and_fetch(
    *,
    client: AsyncClient,
    test_db: AsyncSession,
    employee_headers: dict[str, str],
    store_invoice: StoreInvoice,
    extracted_fields: dict[str, Any] | None,
) -> tuple[dict[str, Any], Sequence[InvoiceRuleResult]]:
    """Run extraction, rule evaluation, and return both public and persisted outcomes."""
    stored = await store_invoice(invoice_pdf_bytes(extracted_fields))
    extracted_invoice = await extract_invoice(
        stored.invoice.id,
        invoices=InvoiceRepository(session=test_db),
        storage=stored.storage,
        text_extractor=PdfTextExtractor(),
        extraction_pipeline=ExtractionPipeline(
            model=FakeExtractionModelClient(extracted_fields or EXTRACTED_FIELDS),
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

    response = await client.get(
        f"/invoices/{stored.invoice.id}", headers=employee_headers
    )

    assert response.status_code == status.HTTP_200_OK

    rows = await RuleResultRepository(test_db).list_by_invoice(stored.invoice.id)

    return response.json(), rows


async def should_record_all_check_pass_for_a_compliant_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Record a passing result for every rule when the invoice is compliant."""
    body, rows = await extract_and_fetch(
        client=client,
        test_db=test_db,
        employee_headers=employee_headers,
        store_invoice=store_invoice,
        extracted_fields=EXTRACTED_FIELDS,
    )

    assert body["status"] == "extracted"

    # Database-level rule code assertion
    assert {row.rule_code for row in rows} == {code.value for code in RuleCode}
    assert all(row.outcome == RuleOutcome.PASS for row in rows)


@pytest.mark.parametrize(
    ("new_fields", "expected_failed_code", "expected_message_parts"),
    [
        (
            {
                "tax_amount": Decimal("0.00"),
                "total_amount": Decimal("1200.00"),
                "line_items": [
                    {"description": "Monitor arm", "amount": Decimal("1200.00")},
                ],
            },
            RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT,
            ("1200.00", "1000.00"),
        ),
        (
            {
                "tax_amount": "10.00",
                "total_amount": "200.00",
                "line_items": [
                    {"description": "Buy A", "amount": "70.00"},
                    {"description": "Buy B", "amount": "30.00"},
                ],
            },
            RuleCode.LINE_ITEM_TOTAL_CONSISTENCY,
            ("110.00", "200.00"),
        ),
        (
            {
                "currency": "JPY",
            },
            RuleCode.CURRENCY_ALLOWED,
            ("JPY", "EUR, GBP, USD"),
        ),
        (
            {
                "invoice_date": "2026-09-01",
            },
            RuleCode.INVOICE_DATE_NOT_IN_FUTURE,
            ("2026-09-01", "2026-08-15"),
        ),
        (
            {
                "invoice_date": "2025-08-15",
            },
            RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW,
            ("365", "90"),
        ),
    ],
)
async def should_flag_each_individual_policy_violation(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
    new_fields: dict[str, Any],
    expected_failed_code: RuleCode,
    expected_message_parts: tuple[str, ...],
) -> None:
    """Fail only the rule targeted by each individual policy violation."""
    extracted_fields = {**EXTRACTED_FIELDS, **new_fields}
    body, rows = await extract_and_fetch(
        client=client,
        test_db=test_db,
        employee_headers=employee_headers,
        store_invoice=store_invoice,
        extracted_fields=extracted_fields,
    )

    assert body["status"] == "extracted"

    assert len(rows) == len(RuleCode)
    for row in rows:
        if row.rule_code == expected_failed_code.value:
            assert row.outcome == RuleOutcome.FAIL
            assert all(part in (row.message or "") for part in expected_message_parts)
        else:
            assert row.outcome == RuleOutcome.PASS


async def should_record_not_applicable_with_no_line_items(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Mark line-item reconciliation as not applicable when no items exist."""
    extracted_fields = {**EXTRACTED_FIELDS, "line_items": []}
    body, rows = await extract_and_fetch(
        client=client,
        test_db=test_db,
        store_invoice=store_invoice,
        employee_headers=employee_headers,
        extracted_fields=extracted_fields,
    )

    assert body["status"] == "extracted"

    assert len(rows) == len(RuleCode)
    for row in rows:
        if row.rule_code == RuleCode.LINE_ITEM_TOTAL_CONSISTENCY.value:
            assert row.outcome == RuleOutcome.NOT_APPLICABLE
        else:
            assert row.outcome == RuleOutcome.PASS


async def should_skip_evaluation_when_extraction_failed(
    client: AsyncClient,
    test_db: AsyncSession,
    store_invoice: StoreInvoice,
    employee_headers: dict[str, str],
) -> None:
    """Skip rule evaluation when invoice extraction fails."""
    body, rows = await extract_and_fetch(
        client=client,
        test_db=test_db,
        employee_headers=employee_headers,
        store_invoice=store_invoice,
        extracted_fields=None,
    )

    assert body["status"] == "extraction_failed"
    assert rows == []
