"""The ``CaseFile`` model plus a loader that enforces every build-abort condition."""

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.database.models.rule_result import RuleOutcome
from app.services.rules.flags import is_explainable, summary_for
from app.services.rules.result import RuleCode
from eval.explanation.build.chunking import IdentifiedChunk
from eval.explanation.build.constants import DIMENSIONS, EVIDENCE_KEYS
from eval.explanation.paths import CASE_YAML, CASES_DIR

HARD_NEGATIVE = "hard-negative"


def _resolve_rule(value: Any) -> Any:
    """Accept a ``RuleCode``, its ``NAME``, or its ``value`` string."""
    if isinstance(value, RuleCode):
        return value
    if isinstance(value, str):
        try:
            return RuleCode[value]
        except KeyError:
            try:
                return RuleCode(value)
            except ValueError:
                raise ValueError(f"rule {value!r} is not a RuleCode") from None
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citations(_Strict):
    """Which chunk IDs a grounded explanation should cite, and the cite gates."""

    ideal: list[str]
    min_recall: float = Field(ge=0.0, le=1.0)
    max_spurious: int = Field(ge=0)


class Check(_Strict):
    """One deterministic regex assertion over the generated narrative."""

    id: str
    kind: Literal["must_contain", "must_absent"]
    pattern: str

    @field_validator("pattern")
    @classmethod
    def _pattern_compiles(cls, pattern: str) -> str:
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(
                f"check pattern {pattern!r} does not compile: {exc}"
            ) from exc
        return pattern


class Rubric(_Strict):
    """One judge-scored statement about the narrative."""

    id: str
    severity: Literal["must", "should"]
    statement: str


class Grading(_Strict):
    """The per-case scoring spec: citation gates, deterministic checks, rubric."""

    citations: Citations
    checks: list[Check]
    rubric: list[Rubric]


class CaseFile(_Strict):
    """A loaded, fully validated explanation golden-set case."""

    title: str
    rule: RuleCode
    dimensions: list[str] = Field(min_length=1)
    evidence: dict[str, str | int | list[str]]
    context: list[str]
    grading: Grading
    notes: str | None = None
    summary: str = ""  # Derived at load via ``summary_for``

    @field_validator("rule", mode="before")
    @classmethod
    def _coerce_rule(cls, value: Any) -> Any:
        rule = _resolve_rule(value)
        if isinstance(rule, RuleCode) and not is_explainable(rule):
            raise ValueError(f"rule {rule.value!r} is not an Explainable Rule")
        return rule

    @field_validator("dimensions")
    @classmethod
    def _known_dimensions(cls, dimensions: list[str]) -> list[str]:
        unknown = sorted(set(dimensions) - DIMENSIONS)
        if unknown:
            raise ValueError(f"unknown dimension(s) {unknown}")
        return dimensions

    @field_validator("context")
    @classmethod
    def _reject_duplicate_context(cls, context: list[str]) -> list[str]:
        seen = {cid for cid in context if context.count(cid) > 1}
        if seen:
            raise ValueError(f"context has duplicate IDs {sorted(seen)}")
        return context

    @model_validator(mode="after")
    def _check_evidence_keys(self) -> "CaseFile":
        expected = EVIDENCE_KEYS[self.rule]
        if self.evidence.keys() != expected:
            raise ValueError(
                f"evidence keys {sorted(self.evidence)} do not match the "
                f"{self.rule.value} contract {sorted(expected)}"
            )
        return self

    @model_validator(mode="after")
    def _check_grading_id_uniqueness(self) -> "CaseFile":
        ids = [c.id for c in self.grading.checks] + [r.id for r in self.grading.rubric]
        clashed = sorted({i for i in ids if ids.count(i) > 1})
        if clashed:
            raise ValueError(f"id collision across checks and rubric: {clashed}")
        return self

    @model_validator(mode="after")
    def _check_hard_negative_iff(self) -> "CaseFile":
        by_dimension = HARD_NEGATIVE in self.dimensions
        by_empty_ideal = self.grading.citations.ideal == []
        if by_dimension != by_empty_ideal:
            raise ValueError(
                "hard-negative must hold two ways at once: "
                f"dimension={by_dimension}, empty-ideal={by_empty_ideal}"
            )
        return self

    @model_validator(mode="after")
    def _check_ideal_in_context(self) -> "CaseFile":
        stray = set(self.grading.citations.ideal) - set(self.context)
        if stray:
            raise ValueError(f"ideal citations {sorted(stray)} are not in context")
        return self


def load_case(data: Mapping[str, Any], chunks: Iterable[IdentifiedChunk]) -> CaseFile:
    """Validate one authored case against the chunk set, returning a ``CaseFile``.

    Raises ``ValueError`` on any build-abort condition.
    """
    chunk_ids = [chunk.id for chunk in chunks]
    duplicates = sorted({cid for cid in chunk_ids if chunk_ids.count(cid) > 1})
    if duplicates:
        raise ValueError(f"chunks.json collision: two chunks resolve to {duplicates}")

    case = CaseFile.model_validate(data)

    known = set(chunk_ids)
    missing = [cid for cid in case.context if cid not in known]
    if missing:
        raise ValueError(f"context IDs absent from chunks.json: {missing}")

    summary = summary_for(case.rule, RuleOutcome.FAIL)
    if summary is None:
        raise ValueError(f"rule {case.rule.value!r} has no FAIL summary to explain")

    return case.model_copy(update={"summary": summary})


def iter_case_dirs() -> list[Path]:
    """Every case directory, in sequential numeric-prefix order."""
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir())


def load_case_dir(case_dir: Path, chunks: Iterable[IdentifiedChunk]) -> CaseFile:
    """Load and validate the ``case.yaml`` under ``case_dir``."""
    raw = yaml.safe_load((case_dir / CASE_YAML).read_text())
    return load_case(raw, chunks)
