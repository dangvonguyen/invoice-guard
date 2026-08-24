from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class RetrievedChunk:
    """One policy chunk."""

    chunk_id: UUID
    section_label: str | None
    content: str


class GeneratedExplanation(BaseModel):
    """Schema-constrained fields the generation model must return."""

    narrative: str
    cited_chunk_indexes: list[int] = []


class GenerationClient(Protocol):
    """Call the generation model and return a grounded explanation."""

    async def generate_explanation(
        self,
        *,
        summary: str,
        evidence: dict[str, Any],
        chunks: Sequence[RetrievedChunk],
    ) -> GeneratedExplanation:
        """Explain a review flag, citing only the numbered excerpts given."""
        ...
