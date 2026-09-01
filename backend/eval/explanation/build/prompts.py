"""Resolve a case's ``context`` to chunks and render ``prompt.txt``."""

from collections.abc import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

from app.services.explanations.generation import RetrievedChunk, build_prompt
from eval.explanation.build.casefile import CaseFile
from eval.explanation.build.chunking import PREAMBLE_LABEL, IdentifiedChunk

# Fixed namespace for placeholder chunk IDs. The string ``context`` ID is a
# chunk's real identity in the eval; ``RetrievedChunk`` still needs a ``UUID``,
# so derive a stable one. The namespace is arbitrary but must never change.
_CHUNK_ID_NAMESPACE = NAMESPACE_URL


def placeholder_chunk_id(context_id: str) -> UUID:
    """A deterministic stand-in ``chunk_id`` derived from the string context ID."""
    return uuid5(_CHUNK_ID_NAMESPACE, context_id)


def resolve_context(
    context: list[str], chunks: Iterable[IdentifiedChunk]
) -> list[RetrievedChunk]:
    """Map each ``context`` ID, in order, to its chunk as a ``RetrievedChunk``."""
    by_id = {chunk.id: chunk for chunk in chunks}
    resolved: list[RetrievedChunk] = []
    for context_id in context:
        chunk = by_id[context_id]
        label = None if chunk.label == PREAMBLE_LABEL else chunk.label
        resolved.append(
            RetrievedChunk(
                chunk_id=placeholder_chunk_id(context_id),
                section_label=label,
                content=chunk.content,
            )
        )
    return resolved


def render_case_prompt(case: CaseFile, chunks: Iterable[IdentifiedChunk]) -> str:
    """The exact user message the model receives for ``case``."""
    return build_prompt(
        summary=case.summary,
        evidence=dict(case.evidence),
        chunks=resolve_context(case.context, chunks),
    )
