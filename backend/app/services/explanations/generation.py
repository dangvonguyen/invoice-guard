from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from openai import AsyncOpenAI
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class RetrievedChunk:
    """One policy chunk."""

    chunk_id: UUID
    section_label: str | None
    content: str


class GeneratedExplanation(BaseModel):
    """Schema-constrained fields the generation model must return."""

    narrative: str
    cited_chunk_indexes: list[int] = Field(default_factory=list)


class GenerationClient(Protocol):
    """Call the generation model and return a grounded explanation."""

    @property
    def model(self) -> str: ...

    async def generate_explanation(
        self,
        *,
        summary: str,
        evidence: dict[str, Any],
        chunks: Sequence[RetrievedChunk],
    ) -> GeneratedExplanation:
        """Explain a review flag, citing only the numbered excerpts given."""
        ...


_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string"},
        "cited_chunk_indexes": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["narrative", "cited_chunk_indexes"],
    "additionalProperties": False,
}

_GENERATION_INSTRUCTIONS = (
    "Explain why a policy rule check failed on an invoice, grounded only in "
    "the numbered policy excerpts provided. Cite an excerpt's index in "
    "cited_chunk_indexes only if its content was actually used; never cite an "
    "excerpt you did not rely on, and never state anything not supported by "
    "the excerpts."
)


class OpenAIGenerationClient:
    """`GenerationClient` backed by OpenAI's structured outputs."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def generate_explanation(
        self,
        *,
        summary: str,
        evidence: dict[str, Any],
        chunks: Sequence[RetrievedChunk],
    ) -> GeneratedExplanation:
        response = await self._client.responses.create(
            model=self._model,
            instructions=_GENERATION_INSTRUCTIONS,
            input=_build_user_input(summary=summary, evidence=evidence, chunks=chunks),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "review_flag_explanation",
                    "schema": _OUTPUT_SCHEMA,
                    "strict": True,
                }
            },
        )
        return GeneratedExplanation.model_validate_json(response.output_text)


def _build_user_input(
    *, summary: str, evidence: dict[str, Any], chunks: Sequence[RetrievedChunk]
) -> str:
    excerpts = "\n\n".join(
        f"[{index}] {chunk.section_label or 'Untitled section'}: {chunk.content}"
        for index, chunk in enumerate(chunks)
    )
    return (
        f"Review flag: {summary}\nEvidence: {evidence}\n\nPolicy excerpts:\n{excerpts}"
    )
