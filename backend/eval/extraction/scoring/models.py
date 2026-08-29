"""Frozen result types produced while scoring a run."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.core.config import ModelProvider
from eval.extraction.scoring.constants import LINE_ITEM_SUBFIELDS, RATE_DECIMALS


@dataclass(frozen=True)
class RunConfig:
    """The effective provider/model/execution settings for one run."""

    provider: ModelProvider
    model: str
    max_tokens: int
    concurrency: int

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        if self.concurrency <= 0:
            raise ValueError(f"concurrency must be positive, got {self.concurrency}")


@dataclass(frozen=True)
class FieldComparison:
    """One expected/actual pair and whether it matched, in serialized form."""

    expected: str | None
    actual: str | None
    match: bool


@dataclass(frozen=True)
class LineItemRowComparison:
    """The four subfield comparisons for one positionally-paired row."""

    index: int
    fields: Mapping[str, FieldComparison]

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"index cannot be negative, got {self.index}")


@dataclass(frozen=True)
class LineItemComparison:
    """The line-item scoring for one case."""

    ordered_match: bool
    unordered_match: bool
    expected_count: int
    actual_count: int
    rows: Sequence[LineItemRowComparison]

    def __post_init__(self) -> None:
        if self.expected_count < 0 or self.actual_count < 0:
            raise ValueError(
                f"counts cannot be negative: expected_count={self.expected_count}, "
                f"actual_count={self.actual_count}"
            )

    @property
    def field_matches(self) -> int:
        return sum(fc.match for row in self.rows for fc in row.fields.values())

    @property
    def field_total(self) -> int:
        return sum(len(row.fields) for row in self.rows)


@dataclass(frozen=True)
class CaseScore:
    """The full scoring of one golden case: success or errored."""

    name: str
    dimensions: tuple[str, ...]
    error: str | None
    fully_correct: bool
    confidence: str | None
    confidence_reason: str | None
    latency_ms: int
    fields: Mapping[str, FieldComparison] | None
    line_items: LineItemComparison | None
    errored_line_item_field_total: int = 0

    def __post_init__(self) -> None:
        if self.is_errored and (self.fields is not None or self.line_items is not None):
            raise ValueError(
                "an errored CaseScore cannot carry fields or line_items scoring data"
            )

    @property
    def is_errored(self) -> bool:
        return self.error is not None

    @property
    def line_item_field_matches(self) -> int:
        if self.line_items is not None:
            return self.line_items.field_matches
        return 0

    @property
    def line_item_field_total(self) -> int:
        if self.line_items is not None:
            return self.line_items.field_total
        return self.errored_line_item_field_total

    @classmethod
    def errored(
        cls,
        name: str,
        dimensions: Sequence[str],
        message: str,
        *,
        latency_ms: int,
        expected_line_count: int,
    ) -> CaseScore:
        """Build the scoring for a case whose pipeline call raised."""
        return cls(
            name=name,
            dimensions=tuple(dimensions),
            error=message,
            fully_correct=False,
            confidence=None,
            confidence_reason=None,
            latency_ms=latency_ms,
            fields=None,
            line_items=None,
            errored_line_item_field_total=expected_line_count
            * len(LINE_ITEM_SUBFIELDS),
        )


@dataclass(frozen=True)
class FieldTally:
    """A ``correct`` / ``total`` count with its rounded rate."""

    correct: int
    total: int

    def __post_init__(self) -> None:
        if self.correct < 0 or self.total < 0:
            raise ValueError(
                f"counts cannot be negative: correct={self.correct}, total={self.total}"
            )
        if self.correct > self.total:
            raise ValueError(
                f"correct ({self.correct}) cannot exceed total ({self.total})"
            )

    @property
    def rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.correct / self.total, RATE_DECIMALS)


@dataclass(frozen=True)
class CaseTally:
    """Every aggregate for a set of scored cases, without dimension slices."""

    cases: int
    fully_correct: int
    error_count: int
    field_accuracy: Mapping[str, FieldTally]

    def __post_init__(self) -> None:
        if self.cases < 0 or self.fully_correct < 0 or self.error_count < 0:
            raise ValueError("counts cannot be negative")
        if self.fully_correct > self.cases:
            raise ValueError(
                f"fully_correct ({self.fully_correct}) cannot exceed cases ({self.cases})"
            )
        if self.error_count > self.cases:
            raise ValueError(
                f"error_count ({self.error_count}) cannot exceed cases ({self.cases})"
            )

    @property
    def fully_correct_rate(self) -> float:
        if self.cases == 0:
            return 0.0
        return round(self.fully_correct / self.cases, RATE_DECIMALS)

    @property
    def error_rate(self) -> float:
        if self.cases == 0:
            return 0.0
        return round(self.error_count / self.cases, RATE_DECIMALS)


@dataclass(frozen=True)
class Totals(CaseTally):
    """A whole-run :class:`CaseTally` plus the per-dimension slices."""

    by_dimension: Mapping[str, CaseTally]


@dataclass(frozen=True)
class RunReport:
    """Everything the artifact writers need for one run."""

    config: RunConfig
    timestamp: datetime
    git_commit: str
    git_dirty: bool
    selector: Mapping[str, Sequence[str]] | None
    cases: Sequence[CaseScore]
    totals: Totals
