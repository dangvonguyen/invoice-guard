"""Shared clients for supported large language model providers."""

from functools import lru_cache

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import get_settings, unwrap_secret


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
