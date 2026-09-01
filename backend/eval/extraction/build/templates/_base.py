"""The ``Template`` value object shared by every layout module."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from eval.extraction.build.source import SourceDocument

RenderFn = Callable[[SourceDocument, Mapping[str, str]], bytes]


@dataclass(frozen=True)
class Template:
    """One invoice layout."""

    name: str
    description: str
    optional_slots: frozenset[str]
    default_labels: Mapping[str, str]
    render: RenderFn
