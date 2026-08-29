"""Shared clients for supported large language model providers."""

from functools import lru_cache
from typing import Any, Protocol

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import ModelProvider, get_settings, unwrap_secret


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    """Return the shared async OpenAI client."""
    settings = get_settings()
    return AsyncOpenAI(api_key=unwrap_secret(settings.OPENAI_API_KEY))


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    """Return the shared async Anthropic client."""
    settings = get_settings()
    return AsyncAnthropic(api_key=unwrap_secret(settings.ANTHROPIC_API_KEY))


class StructuredLLM(Protocol):
    """Call a provider for one JSON object constrained to a supplied schema."""

    @property
    def model(self) -> str: ...

    async def complete_json(
        self,
        *,
        instructions: str,
        schema: dict[str, Any],
        schema_name: str,
        user_message: str,
    ) -> str:
        """Return the model's raw JSON text for a single-turn prompt."""
        ...


class OpenAIStructuredLLM:
    """`StructuredLLM` backed by OpenAI."""

    def __init__(self, *, client: AsyncOpenAI, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    async def complete_json(
        self,
        *,
        instructions: str,
        schema: dict[str, Any],
        schema_name: str,
        user_message: str,
    ) -> str:
        response = await self._client.responses.create(
            model=self._model,
            instructions=instructions,
            input=[{"role": "user", "content": user_message}],
            max_output_tokens=self._max_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return response.output_text


class AnthropicStructuredLLM:
    """`StructuredLLM` backed by Anthropic."""

    def __init__(self, *, client: AsyncAnthropic, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    async def complete_json(
        self,
        *,
        instructions: str,
        schema: dict[str, Any],
        schema_name: str,
        user_message: str,
    ) -> str:
        response = await self._client.messages.create(
            max_tokens=self._max_tokens,
            model=self._model,
            system=instructions,
            messages=[{"role": "user", "content": user_message}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        return next(block.text for block in response.content if block.type == "text")


def build_structured_llm(
    *, provider: ModelProvider, model: str, max_tokens: int
) -> StructuredLLM:
    """Return the `StructuredLLM` for the configured provider."""
    if provider == "openai":
        return OpenAIStructuredLLM(
            client=get_openai_client(), model=model, max_tokens=max_tokens
        )
    else:
        return AnthropicStructuredLLM(
            client=get_anthropic_client(), model=model, max_tokens=max_tokens
        )
