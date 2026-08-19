"""Helper operations across tests."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import ExtractionConfidence, Invoice, InvoiceStatus
from app.database.models.rule_result import InvoiceRuleResult, RuleOutcome
from app.database.models.user import User, UserRole


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
