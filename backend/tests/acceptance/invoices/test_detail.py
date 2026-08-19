"""Acceptance scenarios for reading a single invoice's detail."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import ExtractionConfidence
from app.database.models.rule_result import RuleOutcome
from app.database.models.user import User
from tests.support.helpers import add_rule_result, create_invoice

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


HIGH_CONFIDENCE_FIELDS: dict[str, object] = {
    "vendor_name": "Acme Supplies",
    "invoice_date": "2000-01-01",
    "currency": "USD",
    "tax_amount": "50.00",
    "total_amount": "500.00",
    "line_items": [],
}


async def should_return__summary_for_a_confident_extraction(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Surface vendor, date, total, and currency once extraction is trustworthy."""
    invoice = await create_invoice(
        test_db,
        owner_id=employee.id,
        extracted_fields=HIGH_CONFIDENCE_FIELDS,
        confidence=ExtractionConfidence.HIGH,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=employee_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()["data"]
    assert body["invoice_summary"] == {
        "vendor_name": "Acme Supplies",
        "invoice_date": "2000-01-01",
        "total_amount": "500.00",
        "currency": "USD",
    }
    assert body["decision"] is None


async def should_omit_the_summary_when_extraction_confidence_is_low(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Never condense a summary from data the system couldn't ground."""
    invoice = await create_invoice(
        test_db,
        owner_id=employee.id,
        extracted_fields=HIGH_CONFIDENCE_FIELDS,
        confidence=ExtractionConfidence.LOW,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=employee_headers)

    body = response.json()["data"]
    assert body["invoice_summary"] is None


async def should_never_expose_internal_diagnostics_to_the_owner(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Keep an employee's response limited to id, status, summary, decision."""
    invoice = await create_invoice(
        test_db,
        owner_id=employee.id,
        extracted_fields=HIGH_CONFIDENCE_FIELDS,
        confidence=ExtractionConfidence.HIGH,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=employee_headers)

    body = response.json()["data"]
    assert set(body) == {"id", "status", "invoice_summary", "decision"}


async def should_reject_reading_another_employees_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    other_employee_headers: dict[str, str],
) -> None:
    """Return 404 so ownership is never confirmed to a non-owner."""
    invoice = await create_invoice(test_db, owner_id=employee.id)

    response = await client.get(
        f"/invoices/{invoice.id}", headers=other_employee_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def should_reject_unauthenticated_reads(
    client: AsyncClient, test_db: AsyncSession, employee: User
) -> None:
    """Require authentication before reading an invoice."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_return_the_reviewer_projection_for_a_finance_reviewer(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Give a reviewer the employee identity, raw fields, and review flags."""
    invoice = await create_invoice(
        test_db,
        owner_id=employee.id,
        extracted_fields=HIGH_CONFIDENCE_FIELDS,
        confidence=ExtractionConfidence.LOW,
        confidence_reason="not found in source text: total_amount",
    )
    await add_rule_result(
        test_db,
        invoice_id=invoice.id,
        rule_code="currency_allowed",
        outcome=RuleOutcome.FAIL,
        evidence={"currency": "JPY"},
    )
    await add_rule_result(
        test_db,
        invoice_id=invoice.id,
        rule_code="invoice_date_not_in_future",
        outcome=RuleOutcome.PASS,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=reviewer_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()["data"]
    assert body["employee"]["id"] == str(employee.id)
    assert body["employee"]["email"] == employee.email
    assert body["extracted_fields"] == HIGH_CONFIDENCE_FIELDS
    assert body["confidence"] == "low"
    assert body["confidence_reason"] == "not found in source text: total_amount"
    assert len(body["review_flags"]) == 1
    assert body["review_flags"][0]["code"] == "currency_allowed"
    assert body["review_flags"][0]["evidence"] == {"currency": "JPY"}
    assert body["decision"] is None


async def should_let_a_reviewer_read_an_invoice_they_do_not_own(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    reviewer_headers: dict[str, str],
) -> None:
    """Grant reviewers access regardless of ownership."""
    invoice = await create_invoice(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=reviewer_headers)

    assert response.status_code == status.HTTP_200_OK


async def should_give_a_reviewer_the_normal_view_of_their_own_invoice(
    client: AsyncClient,
    test_db: AsyncSession,
    finance_reviewer: User,
    reviewer_headers: dict[str, str],
) -> None:
    """A reviewer submitting their own invoice sees it like any employee."""
    invoice = await create_invoice(
        test_db,
        owner_id=finance_reviewer.id,
        extracted_fields=HIGH_CONFIDENCE_FIELDS,
        confidence=ExtractionConfidence.HIGH,
    )
    await test_db.commit()

    response = await client.get(f"/invoices/{invoice.id}", headers=reviewer_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()["data"]
    assert set(body) == {"id", "status", "invoice_summary", "decision"}
