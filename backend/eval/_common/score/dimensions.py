"""Ordered collection of the dimension tags a set of scored cases carries."""

from collections.abc import Iterable
from typing import Protocol


class _HasDimensions(Protocol):
    @property
    def dimensions(self) -> tuple[str, ...]: ...


def dimension_tags(results: Iterable[_HasDimensions]) -> list[str]:
    """Every distinct dimension tag across ``results``, in first-seen order."""
    seen: dict[str, None] = {}
    for result in results:
        for tag in result.dimensions:
            seen.setdefault(tag, None)
    return list(seen)
