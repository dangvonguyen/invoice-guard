from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import ModelProvider
from app.core.llm import StructuredLLM, build_structured_llm


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


class LLMGenerationClient:
    """`GenerationClient` backed by a structured-output LLM."""

    def __init__(self, *, llm: StructuredLLM) -> None:
        self._llm = llm

    @property
    def model(self) -> str:
        return self._llm.model

    async def generate_explanation(
        self,
        *,
        summary: str,
        evidence: dict[str, Any],
        chunks: Sequence[RetrievedChunk],
    ) -> GeneratedExplanation:
        raw = await self._llm.complete_json(
            instructions=_GENERATION_INSTRUCTIONS,
            schema=_OUTPUT_SCHEMA,
            schema_name="review_flag_explanation",
            user_message=_build_prompt(
                summary=summary, evidence=evidence, chunks=chunks
            ),
        )
        return GeneratedExplanation.model_validate_json(raw)


def build_generation_client(
    *, provider: ModelProvider, model: str, max_tokens: int
) -> GenerationClient:
    """Return the `GenerationClient` for the configured generation provider."""
    return LLMGenerationClient(
        llm=build_structured_llm(provider=provider, model=model, max_tokens=max_tokens)
    )


def _build_prompt(
    *, summary: str, evidence: dict[str, Any], chunks: Sequence[RetrievedChunk]
) -> str:
    excerpts = "\n\n".join(
        f"[{index}] {chunk.section_label or 'Untitled section'}: {chunk.content}"
        for index, chunk in enumerate(chunks)
    )
    return (
        f"Review flag: {summary}\nEvidence: {evidence}\n\nPolicy excerpts:\n{excerpts}"
    )
