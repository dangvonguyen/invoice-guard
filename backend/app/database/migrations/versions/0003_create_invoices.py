"""Create invoices.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-11 11:04:35.209889

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "invoices",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "upload_failed", name="invoice_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_invoices_owner_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_invoices_storage_key")),
    )
    op.create_index(
        op.f("ix_invoices_owner_id"), "invoices", ["owner_id"], unique=False
    )
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_owner_id"), table_name="invoices")
    op.drop_table("invoices")
    sa.Enum(name="invoice_status").drop(op.get_bind(), checkfirst=True)
