"""Initial schema.

Squashes the incremental migrations (users, invoices, extraction fields,
rule results, policy documents, decisions, explanations) into a single
baseline.

Revision ID: 0001
Revises:
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.database.models.policy_document import EMBEDDING_DIMENSIONS

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
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
        "users",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("employee", "finance_reviewer", name="user_role"),
            server_default="employee",
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_table(
        "invoices",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "upload_failed",
                "processing",
                "processing_error",
                "awaiting_review",
                "approved",
                "rejected",
                name="invoice_status",
            ),
            server_default="processing",
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column(
            "extracted_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "confidence",
            sa.Enum("high", "low", name="extraction_confidence"),
            nullable=True,
        ),
        sa.Column("confidence_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_invoices_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_invoices_storage_key")),
    )
    op.create_index(
        op.f("ix_invoices_owner_id"), "invoices", ["owner_id"], unique=False
    )
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"], unique=False)
    op.create_table(
        "policy_doc_chunks",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("policy_document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_label", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=EMBEDDING_DIMENSIONS), nullable=False),
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
            ["decided_by_id"],
            ["users.id"],
            name=op.f("fk_invoice_decisions_decided_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_invoice_decisions_invoice_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_decisions")),
        sa.UniqueConstraint("invoice_id", name=op.f("uq_invoice_decisions_invoice_id")),
    )
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
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
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
    op.create_table(
        "explanations",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("rule_result_id", sa.Uuid(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
    op.drop_index(
        op.f("ix_invoice_rule_results_invoice_id"), table_name="invoice_rule_results"
    )
    op.drop_table("invoice_rule_results")
    op.drop_table("invoice_decisions")
    op.drop_index(
        op.f("ix_policy_doc_chunks_policy_document_id"), table_name="policy_doc_chunks"
    )
    op.drop_table("policy_doc_chunks")
    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_owner_id"), table_name="invoices")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(
        "uq_policy_documents_single_active",
        table_name="policy_documents",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_index(op.f("ix_policy_documents_status"), table_name="policy_documents")
    op.drop_table("policy_documents")
