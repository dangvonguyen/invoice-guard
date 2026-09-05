"""Create invoice rule results.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "invoice_rule_results",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum("pass", "fail", "not_applicable", name="rule_result_outcome"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_invoice_rule_results_invoice_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_rule_results")),
    )
    op.create_index(
        op.f("ix_invoice_rule_results_invoice_id"),
        "invoice_rule_results",
        ["invoice_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_invoice_rule_results_invoice_id"), table_name="invoice_rule_results"
    )
    op.drop_table("invoice_rule_results")
    sa.Enum(name="rule_result_outcome").drop(op.get_bind(), checkfirst=True)
