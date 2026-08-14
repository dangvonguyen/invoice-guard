"""Add extracted fields and confidence.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-14 01:23:31.449155

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'extracted'")
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'extraction_failed'")

    extraction_confidence = sa.Enum("high", "low", name="extraction_confidence")
    extraction_confidence.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "invoices",
        sa.Column(
            "extracted_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "confidence",
            sa.Enum("high", "low", name="extraction_confidence"),
            nullable=True,
        ),
    )
    op.add_column("invoices", sa.Column("confidence_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("invoices", "confidence_reason")
    op.drop_column("invoices", "confidence")
    op.drop_column("invoices", "extracted_fields")
    sa.Enum(name="extraction_confidence").drop(op.get_bind(), checkfirst=True)

    # PostgreSQL cannot remove enum values in place. Map extraction-only states
    # back to pending before replacing the type with its previous definition.
    op.execute(
        "UPDATE invoices SET status = 'pending' "
        "WHERE status IN ('extracted', 'extraction_failed')"
    )
    previous_invoice_status = sa.Enum(
        "pending", "upload_failed", name="invoice_status_previous"
    )
    previous_invoice_status.create(op.get_bind())
    op.execute("ALTER TABLE invoices ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status TYPE invoice_status_previous "
        "USING status::text::invoice_status_previous"
    )
    sa.Enum(name="invoice_status").drop(op.get_bind())
    op.execute("ALTER TYPE invoice_status_previous RENAME TO invoice_status")
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'pending'::invoice_status"
    )
