"""The embedding model's client boundary.

Shared collaborator between policy-document ingestion and the RAG
exception-explanation query path.
"""

from typing import Protocol

from openai import AsyncOpenAI

EMBEDDING_DIMENSIONS = 1536


class EmbeddingClient(Protocol):
    """Turn text into fixed-length embedding vectors."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, in the same order."""
        ...


class OpenAIEmbeddingClient:
    """`EmbeddingClient` backed by OpenAI's embeddings API."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
