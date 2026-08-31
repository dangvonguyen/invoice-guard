"""Scaffolding shared by the extraction and explanation scoring harnesses."""

import time
from collections.abc import Sequence

from anthropic import APIConnectionError as _AnthropicConnError
from anthropic import AuthenticationError as _AnthropicAuthError
from openai import APIConnectionError as _OpenAIConnError
from openai import AuthenticationError as _OpenAIAuthError

# Provider errors that mean no case can succeed — abort the whole run.
ABORTING_ERRORS = (
    _OpenAIAuthError,
    _OpenAIConnError,
    _AnthropicAuthError,
    _AnthropicConnError,
)


class ScoringError(RuntimeError):
    """An operational failure that aborts the run before any artifact is written."""


def elapsed_ms(start: float) -> int:
    """Milliseconds since a :func:`time.perf_counter` reading."""
    return round((time.perf_counter() - start) * 1000)


def selector(
    names: Sequence[str], dimensions: Sequence[str]
) -> dict[str, list[str]] | None:
    """The report's record of how a run was narrowed, or ``None`` for a bare run."""
    if names:
        return {"names": list(names)}
    if dimensions:
        return {"dimensions": list(dimensions)}
    return None
