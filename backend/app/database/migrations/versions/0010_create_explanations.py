"""Create explanations.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "explanations",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("rule_result_id", sa.Uuid(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("citations", JSONB(), nullable=False),
        sa.Column("generated_by_model", sa.String(length=128), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["rule_result_id"],
            ["invoice_rule_results.id"],
            name=op.f("fk_explanations_rule_result_id_invoice_rule_results"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_explanations")),
        sa.UniqueConstraint(
            "rule_result_id", name=op.f("uq_explanations_rule_result_id")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("explanations")
