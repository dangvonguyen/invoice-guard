"""Rename invoice status values to match the revised lifecycle.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_STATUSES = (
    "upload_failed",
    "processing",
    "processing_error",
    "awaiting_review",
    "approved",
    "rejected",
)
_OLD_STATUSES = (
    "pending",
    "upload_failed",
    "extracted",
    "extraction_failed",
)


def upgrade() -> None:
    """Upgrade schema."""
    new_invoice_status = sa.Enum(*_NEW_STATUSES, name="invoice_status_new")
    new_invoice_status.create(op.get_bind())

    op.execute("ALTER TABLE invoices ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status TYPE invoice_status_new "
        "USING (CASE status::text "
        "WHEN 'upload_failed' THEN 'upload_failed' "
        "WHEN 'pending' THEN 'processing' "
        "WHEN 'extracted' THEN 'awaiting_review' "
        "WHEN 'extraction_failed' THEN 'processing_error' "
        "END)::invoice_status_new"
    )

    sa.Enum(name="invoice_status").drop(op.get_bind())
    op.execute("ALTER TYPE invoice_status_new RENAME TO invoice_status")
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'processing'::invoice_status"
    )


def downgrade() -> None:
    """Downgrade schema."""
    previous_invoice_status = sa.Enum(*_OLD_STATUSES, name="invoice_status_previous")
    previous_invoice_status.create(op.get_bind())

    op.execute("ALTER TABLE invoices ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status TYPE invoice_status_previous "
        "USING (CASE status::text "
        "WHEN 'upload_failed' THEN 'upload_failed' "
        "WHEN 'processing' THEN 'pending' "
        "WHEN 'awaiting_review' THEN 'extracted' "
        "WHEN 'processing_error' THEN 'extraction_failed' "
        # approved/rejected postdate this schema; fold back to the closest
        # pre-decision terminal state rather than losing the row.
        "WHEN 'approved' THEN 'extracted' "
        "WHEN 'rejected' THEN 'extracted' "
        "END)::invoice_status_previous"
    )

    sa.Enum(name="invoice_status").drop(op.get_bind())
    op.execute("ALTER TYPE invoice_status_previous RENAME TO invoice_status")
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'pending'::invoice_status"
    )
