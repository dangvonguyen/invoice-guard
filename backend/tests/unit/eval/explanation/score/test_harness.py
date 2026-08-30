"""Specify the scoring harness: history gating, judge wiring, provider aborts."""

from collections.abc import Sequence
from pathlib import Path

import pytest
from openai import APIConnectionError

from app.services.explanations.generation import GeneratedExplanation, RetrievedChunk
from eval._common.score.harness_support import ScoringError
from eval.explanation import paths
from eval.explanation.build.casefile import Rubric
from eval.explanation.score import harness
from eval.explanation.score.judge import JudgeVerdicts
from eval.explanation.score.results import RunConfig

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _StubConnError(APIConnectionError):
    """A real ``APIConnectionError`` (so ``ABORTING_ERRORS`` catches it) built
    without the vendored ``httpx`` request the SDK constructor demands.
    """

    def __init__(self) -> None:
        Exception.__init__(self, "stubbed provider connection error")


class _StubClient:
    """Returns one fixed explanation for every case, or raises a fixed error."""

    model = "stub-model"

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error

    async def generate_explanation(
        self,
        *,
        summary: str,
        evidence: dict[str, object],
        chunks: Sequence[RetrievedChunk],
    ) -> GeneratedExplanation:
        if self._error is not None:
            raise self._error
        return GeneratedExplanation(
            narrative="Filed 30 days late.", cited_chunk_indexes=[0]
        )


class _StubJudge:
    """Passes every rubric statement, or raises a fixed error."""

    model = "stub-judge"

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error

    async def score_rubric(
        self,
        *,
        narrative: str,
        summary: str,
        evidence: dict[str, object],
        chunks: Sequence[RetrievedChunk],
        rubric: Sequence[Rubric],
    ) -> JudgeVerdicts:
        if self._error is not None:
            raise self._error
        return JudgeVerdicts.model_validate(
            {
                "results": [
                    {"id": item.id, "passed": True, "reason": "ok"} for item in rubric
                ]
            }
        )


@pytest.fixture
def _redirect_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(paths, "HISTORY_PATH", tmp_path / "history.jsonl")
    return tmp_path


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    client: _StubClient | None = None,
    judge: _StubJudge | None = None,
) -> None:
    monkeypatch.setattr(
        harness, "build_generation_client", lambda **_: client or _StubClient()
    )
    monkeypatch.setattr(
        harness, "build_judge_client", lambda **_: judge or _StubJudge()
    )


_CONFIG = RunConfig(
    provider="openai",
    model="gpt-5-mini",
    max_tokens=256,
    concurrency=2,
    judge_provider="openai",
    judge_model="gpt-5-mini",
    judge_max_tokens=256,
)


async def should_append_a_history_line_for_a_whole_set_run(
    _redirect_artifacts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch)

    report, run_path = await harness.run(config=_CONFIG, names=[], dimensions=[])

    assert run_path.exists()
    history = _redirect_artifacts / "history.jsonl"
    assert len(history.read_text().splitlines()) == 1
    # the stub judge passes every rubric statement, so full == deterministic
    assert all(case.judge is not None for case in report.cases)
    assert all(case.full_pass == case.deterministic_pass for case in report.cases)


async def should_not_append_history_for_a_dimension_run(
    _redirect_artifacts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch)

    _, run_path = await harness.run(
        config=_CONFIG, names=[], dimensions=["clean-passage"]
    )

    assert run_path.exists()
    assert not (_redirect_artifacts / "history.jsonl").exists()


async def should_abort_before_writing_any_artifact_on_a_provider_connection_error(
    _redirect_artifacts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch, client=_StubClient(error=_StubConnError()))

    with pytest.raises(ScoringError):
        await harness.run(config=_CONFIG, names=[], dimensions=[])

    assert not (_redirect_artifacts / "runs").exists()
    assert not (_redirect_artifacts / "history.jsonl").exists()


async def should_abort_before_writing_any_artifact_on_a_judge_connection_error(
    _redirect_artifacts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch, judge=_StubJudge(error=_StubConnError()))

    with pytest.raises(ScoringError):
        await harness.run(config=_CONFIG, names=[], dimensions=[])

    assert not (_redirect_artifacts / "runs").exists()
    assert not (_redirect_artifacts / "history.jsonl").exists()


async def should_error_a_case_when_the_judge_call_raises(
    _redirect_artifacts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch, judge=_StubJudge(error=RuntimeError("no JSON")))

    report, _ = await harness.run(
        config=_CONFIG, names=["001_submission_window_overdue"], dimensions=[]
    )

    (case,) = report.cases
    assert case.is_errored
    assert "judge call failed" in (case.error or "")
    assert (_redirect_artifacts / "runs").exists()
