"""Orchestrator: authored case dir -> ``source.pdf`` / extracted text / expected.

Also regenerates the per-set artifacts: the expected-fields JSON schema (from the
extraction model) and ``formats.md`` (from the template registry).
"""

import json
from pathlib import Path
from typing import Any

import yaml

from app.services.extraction.model import ExtractedInvoice
from app.services.extraction.text import PdfTextExtractor
from eval.extraction.generation.constants import BASE_LABELS, LABEL_SLOTS
from eval.extraction.generation.models import SourceDocument, provided_optionals
from eval.extraction.generation.projection import project
from eval.extraction.generation.templates import TEMPLATES, get_template
from eval.extraction.generation.templates._base import Template
from eval.paths import (
    CASE_YAML,
    CASES_DIR,
    EXPECTED_JSON,
    FORMATS_PATH,
    SCHEMA_PATH,
    SOURCE_EXTRACTED_TXT,
    SOURCE_JSON,
    SOURCE_PDF,
)

_extractor = PdfTextExtractor()


def generate_all() -> None:
    """Regenerate every case plus the per-set schema and formats registry."""
    for case_dir in sorted(p for p in CASES_DIR.iterdir() if p.is_dir()):
        generate_case(case_dir)
    emit_schema()
    write_formats_md()


def generate_case(case_dir: Path) -> None:
    """Render one case and write its three generated files."""
    case = _load_case(case_dir)
    doc = SourceDocument.model_validate_json((case_dir / SOURCE_JSON).read_text())
    template = get_template(case["template"])

    _check_label_overrides(case_dir, case)
    _check_capabilities(case_dir, doc, template)

    labels = {**template.default_labels, **(case.get("label_overrides") or {})}
    pdf_bytes = template.render(doc, labels)

    (case_dir / SOURCE_PDF).write_bytes(pdf_bytes)
    (case_dir / SOURCE_EXTRACTED_TXT).write_text(_extractor.extract_text(pdf_bytes))
    (case_dir / EXPECTED_JSON).write_text(_dump_json(project(doc)))


def emit_schema() -> None:
    """Write the expected-fields JSON schema from the extraction model."""
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(_dump_json(ExtractedInvoice.model_json_schema()))


def write_formats_md() -> None:
    """Render ``formats.md`` from the template registry."""
    FORMATS_PATH.write_text(render_formats_md(TEMPLATES))


def render_formats_md(templates: tuple[Template, ...]) -> str:
    """Return the ``formats.md`` body for a template tuple (pure, testable)."""
    lines = [
        "# Invoice layout templates",
        "",
        "Generated from the template registry by `python -m eval.extraction.generation`.",
        "Do not edit by hand.",
        "",
    ]
    for tmpl in templates:
        non_default = {
            slot: value
            for slot, value in tmpl.default_labels.items()
            if BASE_LABELS[slot] != value
        }
        lines.append(f"## `{tmpl.name}`")
        lines.append("")
        lines.append(tmpl.description)
        lines.append("")
        lines.append(f"- **Slots:** {_fmt_set(tmpl.optional_slots)}")
        lines.append(f"- **Non-default labels:** {_fmt_map(non_default)}")
        lines.append("")
    return "\n".join(lines)


def _load_case(case_dir: Path) -> dict[str, Any]:
    case = yaml.safe_load((case_dir / CASE_YAML).read_text())
    if not isinstance(case, dict) or "template" not in case:
        raise ValueError(
            f"{case_dir.name}/{CASE_YAML}: missing required 'template' key"
        )
    return case


def _check_label_overrides(case_dir: Path, case: dict[str, Any]) -> None:
    overrides = case.get("label_overrides") or {}
    unknown = set(overrides) - LABEL_SLOTS
    if unknown:
        raise ValueError(
            f"{case_dir.name}: label_overrides has unknown slots {sorted(unknown)}; "
            f"allowed: {sorted(LABEL_SLOTS)}"
        )


def _check_capabilities(
    case_dir: Path, doc: SourceDocument, template: Template
) -> None:
    unplaceable = provided_optionals(doc) - template.optional_slots
    if unplaceable:
        raise ValueError(
            f"{case_dir.name}: template {template.name!r} cannot place "
            f"{sorted(unplaceable)} (declares slots {sorted(template.optional_slots)})"
        )


def _dump_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _fmt_set(values: frozenset[str]) -> str:
    return ", ".join(f"`{v}`" for v in sorted(values)) or "_none_"


def _fmt_map(values: dict[str, str]) -> str:
    return ", ".join(f"`{k}` = {v!r}" for k, v in sorted(values.items())) or "_none_"
