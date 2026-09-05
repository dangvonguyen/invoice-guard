"""Add user name and role.

Revision ID: 0900
Revises: 0010
Create Date: 2026-08-07 02:14:06.523376

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "users",
        "id",
        existing_type=sa.String(),
        type_=postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        postgresql_using="id::uuid",
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(),
        type_=sa.String(length=254),
    )
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(),
        type_=sa.String(length=255),
    )
    user_role = sa.Enum("employee", "finance_reviewer", name="user_role")
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("name", sa.String(length=255), nullable=True))
    op.execute(sa.text("UPDATE users SET name = email"))
    op.alter_column("users", "name", nullable=False)
    op.add_column(
        "users",
        sa.Column(
            "role",
            user_role,
            server_default="employee",
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
    op.drop_column("users", "name")
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        type_=sa.String(),
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=254),
        type_=sa.String(),
    )
    op.alter_column(
        "users",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(),
        server_default=None,
        postgresql_using="id::text",
    )
