"""Database model for a finance reviewer's final decision on an invoice."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.user import User


class InvoiceDecisionOutcome(StrEnum):
    """The two legal final outcomes for an invoice decision."""

    APPROVED = "approved"
    REJECTED = "rejected"


class InvoiceDecision(Base):
    """Record the one final decision made on an invoice.

    `invoice_id` is unique so the database itself enforces "exactly one
    decision per invoice" - the unique constraint is the sole authority
    for rejecting a second, concurrent decision attempt.
    """

    __tablename__ = "invoice_decisions"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        unique=True,
    )
    outcome: Mapped[InvoiceDecisionOutcome] = mapped_column(
        Enum(
            InvoiceDecisionOutcome,
            name="invoice_decision_outcome",
            values_callable=lambda outcomes: [o.value for o in outcomes],
        ),
    )
    reason: Mapped[str] = mapped_column(Text)
    decided_by_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    decided_by: Mapped[User] = relationship(lazy="raise")
