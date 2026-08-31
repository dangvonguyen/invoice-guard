"""The explicit layout-template registry."""

from eval.extraction.build.templates import (
    classic_column,
    itemized_vat,
    service_minimal,
)
from eval.extraction.build.templates._base import Template

TEMPLATES: tuple[Template, ...] = (
    classic_column.TEMPLATE,
    itemized_vat.TEMPLATE,
    service_minimal.TEMPLATE,
)

_BY_NAME: dict[str, Template] = {t.name: t for t in TEMPLATES}


def get_template(name: str) -> Template:
    """Return the registered template, or raise naming the known names."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise KeyError(
            f"unknown template {name!r}; known: {sorted(_BY_NAME)}"
        ) from None
