"""Database models for the ingested expense-policy handbook and its chunks."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.services.embeddings.client import EMBEDDING_DIMENSIONS


class PolicyDocumentStatus(StrEnum):
    """Lifecycle states for an ingested policy handbook."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"


class PolicyDocument(Base):
    """Represent one ingested version of the expense-policy handbook."""

    __tablename__ = "policy_documents"
    __table_args__ = (
        Index(
            "uq_policy_documents_single_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[PolicyDocumentStatus] = mapped_column(
        Enum(
            PolicyDocumentStatus,
            name="policy_document_status",
            values_callable=lambda statuses: [s.value for s in statuses],
        ),
        server_default=PolicyDocumentStatus.ACTIVE.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PolicyDocChunk(Base):
    """Represent one embedded, retrievable chunk of a policy document."""

    __tablename__ = "policy_doc_chunks"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    policy_document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("policy_documents.id"),
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    section_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
