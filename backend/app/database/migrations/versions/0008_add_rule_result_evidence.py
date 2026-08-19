"""Add structured evidence to rule results and drop the free-text message.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "invoice_rule_results",
        sa.Column(
            "evidence",
            pg.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.drop_column("invoice_rule_results", "message")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "invoice_rule_results",
        sa.Column("message", sa.Text(), nullable=True),
    )
    op.drop_column("invoice_rule_results", "evidence")
