"""Specify the orchestrator: validation, capability checks and file output."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from eval.extraction.build import render

pytestmark = pytest.mark.unit

_MINIMAL_SOURCE: dict[str, Any] = {
    "vendor": {"name": "Acme Supplies Ltd"},
    "invoice": {
        "number": "INV-1",
        "date": "2024-03-07",
        "currency": "USD",
        "tax_amount": None,
        "total_amount": "100.00",
    },
    "line_items": [{"description": "Widget", "amount": "100.00"}],
    "render": {
        "date_format": "iso",
        "amount_grouping": True,
        "currency_display": "code",
    },
}


def _write_case(
    parent: Path, *, name: str, case: dict[str, Any], source: dict[str, Any]
) -> Path:
    case_dir = parent / name
    case_dir.mkdir()
    (case_dir / "case.yaml").write_text(yaml.safe_dump(case))
    (case_dir / "source.json").write_text(json.dumps(source))
    return case_dir


def should_write_the_three_generated_files(tmp_path: Path) -> None:
    case_dir = _write_case(
        tmp_path,
        name="900_probe",
        case={"template": "classic-column"},
        source=_MINIMAL_SOURCE,
    )

    render.generate_case(case_dir)

    expected = json.loads((case_dir / "expected.json").read_text())
    assert expected["vendor_name"] == "Acme Supplies Ltd"
    assert (case_dir / "source.pdf").read_bytes().startswith(b"%PDF")
    assert "Acme Supplies Ltd" in (case_dir / "source.extracted.txt").read_text()


def should_regenerate_byte_identically(tmp_path: Path) -> None:
    case_dir = _write_case(
        tmp_path,
        name="900_probe",
        case={"template": "classic-column"},
        source=_MINIMAL_SOURCE,
    )

    render.generate_case(case_dir)
    first = (case_dir / "source.pdf").read_bytes()
    render.generate_case(case_dir)
    second = (case_dir / "source.pdf").read_bytes()

    assert first == second


def should_raise_when_a_distractor_has_no_slot_on_the_template(tmp_path: Path) -> None:
    source = {**_MINIMAL_SOURCE, "distractors": {"po_number": "PO-7"}}
    case_dir = _write_case(
        tmp_path,
        name="901_unplaceable",
        case={"template": "classic-column"},
        source=source,
    )

    with pytest.raises(ValueError, match=r"901_unplaceable.*classic-column.*po_number"):
        render.generate_case(case_dir)


def should_raise_on_an_unknown_label_slot(tmp_path: Path) -> None:
    case_dir = _write_case(
        tmp_path,
        name="902_badlabel",
        case={"template": "classic-column", "label_overrides": {"nonsense": "X"}},
        source=_MINIMAL_SOURCE,
    )

    with pytest.raises(ValueError, match=r"unknown slots.*nonsense"):
        render.generate_case(case_dir)


def should_raise_on_an_unknown_template(tmp_path: Path) -> None:
    case_dir = _write_case(
        tmp_path,
        name="903_notemplate",
        case={"template": "does-not-exist"},
        source=_MINIMAL_SOURCE,
    )

    with pytest.raises(KeyError, match="unknown template"):
        render.generate_case(case_dir)


def should_apply_a_label_override_to_the_rendered_text(tmp_path: Path) -> None:
    case_dir = _write_case(
        tmp_path,
        name="904_override",
        case={
            "template": "classic-column",
            "label_overrides": {"total_amount": "Balance Due"},
        },
        source=_MINIMAL_SOURCE,
    )

    render.generate_case(case_dir)

    assert "Balance Due" in (case_dir / "source.extracted.txt").read_text()
