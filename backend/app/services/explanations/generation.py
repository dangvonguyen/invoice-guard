from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import ModelProvider
from app.core.llm import get_anthropic_client, get_openai_client


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

    def __init__(self, *, client: AsyncOpenAI, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

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
            input=_build_messages(summary=summary, evidence=evidence, chunks=chunks),
            max_output_tokens=self._max_tokens,
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


class AnthropicGenerationClient:
    """`GenerationClient` backed by Anthropic."""

    def __init__(self, *, client: AsyncAnthropic, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

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
        response = await self._client.messages.create(
            max_tokens=self._max_tokens,
            model=self._model,
            system=_GENERATION_INSTRUCTIONS,
            messages=_build_messages(summary=summary, evidence=evidence, chunks=chunks),
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": _OUTPUT_SCHEMA,
                }
            },
        )
        text = next(block.text for block in response.content if block.type == "text")
        return GeneratedExplanation.model_validate_json(text)


def build_generation_client(
    *, provider: ModelProvider, model: str, max_tokens: int
) -> GenerationClient:
    """Return the `GenerationClient` for the configured generation provider."""
    if provider == "openai":
        return OpenAIGenerationClient(
            client=get_openai_client(), model=model, max_tokens=max_tokens
        )
    else:
        return AnthropicGenerationClient(
            client=get_anthropic_client(), model=model, max_tokens=max_tokens
        )


def _build_messages(
    *, summary: str, evidence: dict[str, Any], chunks: Sequence[RetrievedChunk]
) -> list[Any]:
    excerpts = "\n\n".join(
        f"[{index}] {chunk.section_label or 'Untitled section'}: {chunk.content}"
        for index, chunk in enumerate(chunks)
    )
    content = (
        f"Review flag: {summary}\nEvidence: {evidence}\n\nPolicy excerpts:\n{excerpts}"
    )
    return [{"role": "user", "content": content}]
