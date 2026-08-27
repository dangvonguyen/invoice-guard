"""The explicit layout-template registry."""

from eval.extraction.generation.templates import classic_column
from eval.extraction.generation.templates._base import Template

TEMPLATES: tuple[Template, ...] = (classic_column.TEMPLATE,)

_BY_NAME: dict[str, Template] = {t.name: t for t in TEMPLATES}


def get_template(name: str) -> Template:
    """Return the registered template, or raise naming the known names."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise KeyError(
            f"unknown template {name!r}; known: {sorted(_BY_NAME)}"
        ) from None
