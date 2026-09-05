"""Create claims.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02 15:37:12.824970

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "claims",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "submitted",
                "under_review",
                "returned_for_info",
                "approved",
                "rejected",
                "withdrawn",
                name="claim_status",
            ),
            server_default="submitted",
            nullable=False,
        ),
        sa.Column("expense_title", sa.Text(), nullable=False),
        sa.Column("business_purpose", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "software_hosting",
                "travel_transport",
                "travel_lodging",
                "meals_entertainment",
                "office_supplies",
                "other",
                name="claim_category",
            ),
            nullable=False,
        ),
        sa.Column("cost_center", sa.Text(), nullable=True),
        sa.Column("vendor", sa.Text(), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "original_total_amount", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("certified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attachment_key", sa.String(length=255), nullable=False),
        sa.Column("attachment_filename", sa.String(length=255), nullable=False),
        sa.Column("attachment_content_type", sa.String(length=100), nullable=False),
        sa.Column("attachment_bytes", sa.Integer(), nullable=False),
        sa.Column("assigned_reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_reviewer_id"],
            ["users.id"],
            name=op.f("fk_claims_assigned_reviewer_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_claims_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claims")),
        sa.UniqueConstraint("attachment_key", name=op.f("uq_claims_attachment_key")),
    )
    op.create_index(
        "ix_claims_assigned_reviewer_id_status",
        "claims",
        ["assigned_reviewer_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_claims_owner_id_created_at",
        "claims",
        ["owner_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_claims_status_created_at", "claims", ["status", "created_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_claims_status_created_at", table_name="claims")
    op.drop_index("ix_claims_owner_id_created_at", table_name="claims")
    op.drop_index("ix_claims_assigned_reviewer_id_status", table_name="claims")
    op.drop_table("claims")
    op.execute("DROP TYPE claim_category")
    op.execute("DROP TYPE claim_status")
