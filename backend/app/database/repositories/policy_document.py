"""Database access operations for policy documents and their chunks."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.policy_document import (
    PolicyDocChunk,
    PolicyDocument,
    PolicyDocumentStatus,
)


@dataclass(frozen=True)
class NewPolicyChunk:
    """One chunk ready to persist, produced by ingestion."""

    section_label: str | None
    content: str
    embedding: list[float]


class PolicyDocumentRepository:
    """Repository for performing database operations related to policy documents."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def activate(
        self, *, original_filename: str, chunks: Sequence[NewPolicyChunk]
    ) -> PolicyDocument:
        """Supersede the current active document and activate a new one.

        Serializes concurrent activations with `SELECT ... FOR UPDATE` so two
        uploads racing each other never leave two documents active.
        """
        current_active = (
            await self._session.execute(
                select(PolicyDocument)
                .where(PolicyDocument.status == PolicyDocumentStatus.ACTIVE)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if current_active is not None:
            current_active.status = PolicyDocumentStatus.SUPERSEDED

        document = PolicyDocument(
            original_filename=original_filename,
            status=PolicyDocumentStatus.ACTIVE,
        )
        self._session.add(document)
        await self._session.flush()

        self._session.add_all(
            [
                PolicyDocChunk(
                    policy_document_id=document.id,
                    chunk_index=index,
                    section_label=chunk.section_label,
                    content=chunk.content,
                    embedding=chunk.embedding,
                )
                for index, chunk in enumerate(chunks)
            ]
        )
        await self._session.flush()
        return document

    async def list_all(self) -> Sequence[tuple[PolicyDocument, int]]:
        """Return every document with its chunk count, newest first."""
        chunk_counts = (
            select(
                PolicyDocChunk.policy_document_id,
                func.count().label("chunk_count"),
            )
            .group_by(PolicyDocChunk.policy_document_id)
            .subquery()
        )
        result = await self._session.execute(
            select(PolicyDocument, func.coalesce(chunk_counts.c.chunk_count, 0))
            .outerjoin(
                chunk_counts, chunk_counts.c.policy_document_id == PolicyDocument.id
            )
            .order_by(PolicyDocument.created_at.desc())
        )
        return [(document, count) for document, count in result.all()]
