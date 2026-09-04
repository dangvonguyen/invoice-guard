"""Database model for employee-submitted reimbursement claims.

A claim is one employee's request for reimbursement of a single vendor
document: the attachment, the business context, the entered invoice facts,
and the certification stamped at submission.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.user import User


class ClaimStatus(StrEnum):
    """Lifecycle states for a claim."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    RETURNED_FOR_INFO = "returned_for_info"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ClaimCategory(StrEnum):
    """The fixed set of expense categories an employee may pick from."""

    SOFTWARE_HOSTING = "software_hosting"
    TRAVEL_TRANSPORT = "travel_transport"
    TRAVEL_LODGING = "travel_lodging"
    MEALS_ENTERTAINMENT = "meals_entertainment"
    OFFICE_SUPPLIES = "office_supplies"
    OTHER = "other"


class LineItemSource(StrEnum):
    """Who supplied a given claim line item."""

    REVIEWER = "reviewer"
    EMPLOYEE = "employee"


def _enum_column(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda members: [m.value for m in members],
    )


class Claim(Base):
    """An employee's reimbursement request for one vendor document."""

    __tablename__ = "claims"
    __table_args__ = (
        Index("ix_claims_status_created_at", "status", "created_at"),
        Index("ix_claims_owner_id_created_at", "owner_id", "created_at"),
        Index(
            "ix_claims_assigned_reviewer_id_status", "assigned_reviewer_id", "status"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    status: Mapped[ClaimStatus] = mapped_column(
        _enum_column(ClaimStatus, "claim_status"),
        server_default=ClaimStatus.SUBMITTED.value,
    )

    # Business context
    expense_title: Mapped[str] = mapped_column(Text)
    business_purpose: Mapped[str] = mapped_column(Text)
    category: Mapped[ClaimCategory] = mapped_column(
        _enum_column(ClaimCategory, "claim_category")
    )
    cost_center: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Invoice facts
    vendor: Mapped[str] = mapped_column(Text)
    invoice_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Immutable snapshot of the total at first submit
    original_total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    # Certification
    certified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Attachment
    attachment_key: Mapped[str] = mapped_column(String(255), unique=True)
    attachment_filename: Mapped[str] = mapped_column(String(255))
    attachment_content_type: Mapped[str] = mapped_column(String(100))
    attachment_bytes: Mapped[int] = mapped_column(Integer)

    # Queue assignment
    assigned_reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship(lazy="raise")
    line_items: Mapped[list["ClaimLineItem"]] = relationship(
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ClaimLineItem.position",
    )


class ClaimLineItem(Base):
    """One itemized line on a claim, in submission order."""

    __tablename__ = "claim_line_items"
    __table_args__ = (
        Index("ix_claim_line_items_claim_id", "claim_id"),
        # Positions are 1..n within a claim and never collide.
        UniqueConstraint(
            "claim_id", "position", name="uq_claim_line_items_claim_id_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("claims.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    source: Mapped[LineItemSource] = mapped_column(
        _enum_column(LineItemSource, "line_item_source")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
