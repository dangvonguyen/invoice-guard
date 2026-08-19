"""Database model for the outcome of each policy rule evaluated against an invoice."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RuleOutcome(StrEnum):
    """The result of evaluating one deterministic rule against one invoice."""

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class InvoiceRuleResult(Base):
    """Record one rule's outcome for one evaluated invoice."""

    __tablename__ = "invoice_rule_results"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        index=True,
    )
    # A string rather than a database enum as the rule is expected to grow
    rule_code: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[RuleOutcome] = mapped_column(
        Enum(
            RuleOutcome,
            name="rule_result_outcome",
            values_callable=lambda outcomes: [o.value for o in outcomes],
        ),
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
