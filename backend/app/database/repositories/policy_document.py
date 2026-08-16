"""Database access operations for policy documents and their chunks."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.policy_document import PolicyDocument


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

        Interface under active development by the inner loop driving B1/B2 -
        real transactional behaviour lands with its own integration test.
        """
        raise NotImplementedError
