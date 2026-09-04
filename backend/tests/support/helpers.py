"""Helper operations across tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.claim import Claim, ClaimCategory, ClaimStatus
from app.database.models.invoice import ExtractionConfidence, Invoice, InvoiceStatus
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.database.models.user import User, UserRole


def pdf_bytes(text: str = "") -> bytes:
    """Build a real, parseable single-page PDF containing the given text."""
    pdf = FPDF()
    pdf.add_page()
    if text:
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text=text)
    return bytes(pdf.output())


async def create_user(
    test_db: AsyncSession,
    *,
    email: str,
    role: UserRole = UserRole.EMPLOYEE,
    id: UUID | None = None,
    name: str | None = None,
    hashed_password: str = "unused-password-hash",
) -> User:
    """Insert a user row directly."""
    user = User(
        email=email,
        hashed_password=hashed_password,
        name=name or email.split("@")[0],
        role=role,
        **({"id": id} if id else {}),
    )
    test_db.add(user)
    await test_db.flush()
    return user


async def create_invoice(
    test_db: AsyncSession,
    *,
    owner_id: UUID,
    storage_key: str = "invoice.pdf",
    status: InvoiceStatus = InvoiceStatus.AWAITING_REVIEW,
    extracted_fields: dict[str, object] | None = None,
    confidence: ExtractionConfidence | None = None,
    confidence_reason: str | None = None,
    created_at: datetime | None = None,
) -> Invoice:
    """Insert an invoice row directly, bypassing upload and processing."""
    extra: dict[str, Any] = {}
    if extracted_fields:
        extra["extracted_fields"] = extracted_fields
    if confidence:
        extra["confidence"] = confidence
    if confidence_reason:
        extra["confidence_reason"] = confidence_reason
    if created_at:
        extra["created_at"] = created_at

    invoice = Invoice(
        owner_id=owner_id,
        storage_key=storage_key,
        original_filename=storage_key,
        status=status,
        **extra,
    )
    test_db.add(invoice)
    await test_db.flush()
    return invoice


async def create_claim(
    test_db: AsyncSession,
    *,
    owner_id: UUID,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    expense_title: str = "Annual Figma subscription",
    business_purpose: str = "Design tooling for the product team.",
    category: ClaimCategory = ClaimCategory.SOFTWARE_HOSTING,
    cost_center: str | None = "PRODUCT-DESIGN",
    vendor: str = "Figma Inc.",
    invoice_number: str | None = "FIG-2026-00417",
    invoice_date: date = date(2026, 2, 14),
    total_amount: Decimal = Decimal("144.00"),
    currency: str = "USD",
    attachment_key: str = "claim-attachment-key",
    attachment_filename: str = "figma-invoice.pdf",
    attachment_content_type: str = "application/pdf",
    attachment_bytes: int = 2048,
    created_at: datetime | None = None,
) -> Claim:
    """Insert a claim row directly, bypassing submission."""
    extra: dict[str, Any] = {}
    if created_at:
        extra["created_at"] = created_at

    claim = Claim(
        owner_id=owner_id,
        status=status,
        expense_title=expense_title,
        business_purpose=business_purpose,
        category=category,
        cost_center=cost_center,
        vendor=vendor,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        total_amount=total_amount,
        currency=currency,
        original_total_amount=total_amount,
        certified_at=datetime.now(UTC),
        attachment_key=attachment_key,
        attachment_filename=attachment_filename,
        attachment_content_type=attachment_content_type,
        attachment_bytes=attachment_bytes,
        **extra,
    )
    test_db.add(claim)
    await test_db.flush()
    return claim


async def add_rule_result(
    test_db: AsyncSession,
    *,
    invoice_id: UUID,
    outcome: RuleOutcome,
    rule_code: str = "currency_allowed",
    evidence: dict[str, object] | None = None,
) -> None:
    """Insert a rule-result row directly."""
    test_db.add(
        InvoiceRuleResult(
            invoice_id=invoice_id,
            rule_code=rule_code,
            outcome=outcome,
            evidence=evidence,
        )
    )
    await test_db.flush()
