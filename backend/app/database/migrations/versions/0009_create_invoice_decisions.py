"""Create invoice decisions.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "invoice_decisions",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum("approved", "rejected", name="invoice_decision_outcome"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_invoice_decisions_invoice_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_id"],
            ["users.id"],
            name=op.f("fk_invoice_decisions_decided_by_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_decisions")),
        sa.UniqueConstraint("invoice_id", name=op.f("uq_invoice_decisions_invoice_id")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("invoice_decisions")
    sa.Enum(name="invoice_decision_outcome").drop(op.get_bind(), checkfirst=True)
