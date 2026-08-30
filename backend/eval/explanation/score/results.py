"""Frozen result types produced while scoring an explanation run."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.core.config import ModelProvider
from eval.explanation.score.constants import RATE_DECIMALS


@dataclass(frozen=True)
class RunConfig:
    """The effective provider/model/execution settings for one run."""

    provider: ModelProvider
    model: str
    max_tokens: int
    judge_provider: ModelProvider
    judge_model: str
    judge_max_tokens: int
    concurrency: int

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        if self.judge_max_tokens <= 0:
            raise ValueError(
                f"judge_max_tokens must be positive, got {self.judge_max_tokens}"
            )
        if self.concurrency <= 0:
            raise ValueError(f"concurrency must be positive, got {self.concurrency}")


@dataclass(frozen=True)
class CitationScore:
    """Citation metrics for one case plus whether the citation gate passed."""

    recall: float
    precision: float
    spurious: int
    gate: bool

    def __post_init__(self) -> None:
        if self.spurious < 0:
            raise ValueError(f"spurious cannot be negative, got {self.spurious}")


@dataclass(frozen=True)
class CheckResult:
    """One deterministic regex assertion and whether the narrative satisfied it."""

    id: str
    kind: str
    pattern: str
    passed: bool


@dataclass(frozen=True)
class JudgeResult:
    """One judge-scored rubric statement and the judge's verdict on it."""

    id: str
    severity: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class CheckScore:
    """Every check verdict for one case."""

    results: Sequence[CheckResult]

    @property
    def gate(self) -> bool:
        """Whether every check passed."""
        return all(c.passed for c in self.results)


@dataclass(frozen=True)
class JudgeScore:
    """Every rubric verdict for one case."""

    results: Sequence[JudgeResult]

    @property
    def gate(self) -> bool:
        """Whether every ``severity: must`` statement passed."""
        return all(r.passed for r in self.results if r.severity == "must")


@dataclass(frozen=True)
class CaseResult:
    """The full scoring of one case: success or errored."""

    name: str
    dimensions: tuple[str, ...]
    error: str | None
    narrative: str | None
    raw_indexes: tuple[int, ...]
    cited_ids: tuple[str, ...]
    out_of_range: tuple[int, ...]
    citation: CitationScore | None
    check: CheckScore | None
    judge: JudgeScore | None
    deterministic_pass: bool
    full_pass: bool | None
    latency_ms: int

    def __post_init__(self) -> None:
        if self.is_errored and (
            self.citation is not None
            or self.check is not None
            or self.judge is not None
        ):
            raise ValueError("an errored CaseResult cannot carry scores")
        if self.is_errored and (self.deterministic_pass or self.full_pass):
            raise ValueError("an errored CaseResult cannot pass a gate")

    @property
    def is_errored(self) -> bool:
        return self.error is not None

    @classmethod
    def errored(
        cls,
        name: str,
        dimensions: Sequence[str],
        message: str,
        *,
        latency_ms: int,
    ) -> CaseResult:
        """Build the scoring for a case whose generation call raised."""
        return cls(
            name=name,
            dimensions=tuple(dimensions),
            error=message,
            narrative=None,
            raw_indexes=(),
            cited_ids=(),
            out_of_range=(),
            citation=None,
            check=None,
            judge=None,
            deterministic_pass=False,
            full_pass=None,
            latency_ms=latency_ms,
        )


@dataclass(frozen=True)
class Tally:
    """A ``passed`` / ``total`` count with its rounded rate."""

    passed: int
    total: int

    def __post_init__(self) -> None:
        if self.passed < 0 or self.total < 0:
            raise ValueError(
                f"counts cannot be negative: passed={self.passed}, total={self.total}"
            )
        if self.passed > self.total:
            raise ValueError(
                f"passed ({self.passed}) cannot exceed total ({self.total})"
            )

    @property
    def rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.passed / self.total, RATE_DECIMALS)


@dataclass(frozen=True)
class RunTally:
    """Every deterministic aggregate for a set of scored cases, without slices."""

    cases: int
    errored: int
    scored: int
    deterministic_pass: int
    full_pass: int
    spurious_cases: int
    out_of_range_cases: int
    mean_precision: float
    mean_recall: float
    per_check: Mapping[str, Tally]
    per_must: Mapping[str, Tally]
    per_should: Mapping[str, Tally]

    def __post_init__(self) -> None:
        counts = (
            self.cases,
            self.errored,
            self.scored,
            self.deterministic_pass,
            self.full_pass,
            self.spurious_cases,
            self.out_of_range_cases,
        )
        if any(count < 0 for count in counts):
            raise ValueError("counts cannot be negative")
        if self.errored + self.scored != self.cases:
            raise ValueError(
                f"errored ({self.errored}) + scored ({self.scored}) "
                f"must equal cases ({self.cases})"
            )

    @property
    def error_rate(self) -> float:
        return _rate(self.errored, self.cases)

    @property
    def deterministic_pass_rate(self) -> float:
        return _rate(self.deterministic_pass, self.cases)

    @property
    def full_pass_rate(self) -> float:
        return _rate(self.full_pass, self.cases)

    @property
    def spurious_rate(self) -> float:
        return _rate(self.spurious_cases, self.cases)

    @property
    def out_of_range_rate(self) -> float:
        return _rate(self.out_of_range_cases, self.cases)


@dataclass(frozen=True)
class Totals(RunTally):
    """A whole-run :class:`RunTally` plus the per-dimension slices."""

    by_dimension: Mapping[str, RunTally]


@dataclass(frozen=True)
class RunReport:
    """Everything the artifact writers need for one run."""

    config: RunConfig
    timestamp: datetime
    git_commit: str
    git_dirty: bool
    selector: Mapping[str, Sequence[str]] | None
    cases: Sequence[CaseResult]
    totals: Totals


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, RATE_DECIMALS)
