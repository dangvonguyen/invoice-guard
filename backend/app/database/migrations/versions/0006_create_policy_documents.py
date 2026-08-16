"""Create policy documents and chunks.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.services.embeddings.client import EMBEDDING_DIMENSIONS

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "policy_documents",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "superseded", name="policy_document_status"),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_documents")),
    )
    op.create_index(
        op.f("ix_policy_documents_status"), "policy_documents", ["status"], unique=False
    )
    op.create_index(
        "uq_policy_documents_single_active",
        "policy_documents",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "policy_doc_chunks",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("policy_document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_label", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["policy_document_id"],
            ["policy_documents.id"],
            name=op.f("fk_policy_doc_chunks_policy_document_id_policy_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_doc_chunks")),
    )
    op.create_index(
        op.f("ix_policy_doc_chunks_policy_document_id"),
        "policy_doc_chunks",
        ["policy_document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_policy_doc_chunks_policy_document_id"), table_name="policy_doc_chunks"
    )
    op.drop_table("policy_doc_chunks")
    op.drop_index("uq_policy_documents_single_active", table_name="policy_documents")
    op.drop_index(op.f("ix_policy_documents_status"), table_name="policy_documents")
    op.drop_table("policy_documents")
    sa.Enum(name="policy_document_status").drop(op.get_bind(), checkfirst=True)
