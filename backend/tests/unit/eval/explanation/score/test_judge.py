"""Specify the judge: verdict parsing, must/should gating, missing verdicts."""

from typing import Any, Literal

import pytest

from eval.explanation.build.casefile import Rubric
from eval.explanation.score.judge import (
    JUDGE_OUTPUT_SCHEMA,
    JudgeVerdicts,
    LLMJudgeClient,
    build_judge_prompt,
    to_judge_score,
)

pytestmark = pytest.mark.unit


def _rubric(*specs: tuple[str, Literal["must", "should"]]) -> list[Rubric]:
    return [
        Rubric(id=rid, severity=sev, statement=f"statement {rid}") for rid, sev in specs
    ]


def _verdicts(**passed: bool) -> JudgeVerdicts:
    return JudgeVerdicts.model_validate(
        {
            "results": [
                {"id": rid, "passed": ok, "reason": "because"}
                for rid, ok in passed.items()
            ]
        }
    )


def should_pass_the_must_gate_when_every_must_statement_passed() -> None:
    rubric = _rubric(("a", "must"), ("b", "must"), ("c", "should"))

    score = to_judge_score(rubric, _verdicts(a=True, b=True, c=False))

    assert score.gate is True


def should_fail_the_must_gate_when_any_must_statement_failed() -> None:
    rubric = _rubric(("a", "must"), ("b", "must"))

    score = to_judge_score(rubric, _verdicts(a=True, b=False))

    assert score.gate is False


def should_never_let_a_should_statement_gate() -> None:
    rubric = _rubric(("a", "must"), ("tone", "should"))

    score = to_judge_score(rubric, _verdicts(a=True, tone=False))

    assert score.gate is True


def should_carry_severity_from_the_rubric_not_the_judge() -> None:
    rubric = _rubric(("a", "should"), ("b", "must"))

    score = to_judge_score(rubric, _verdicts(a=False, b=True))

    by_id = {r.id: r for r in score.results}
    assert by_id["a"].severity == "should"
    assert by_id["b"].severity == "must"


def should_record_a_missing_verdict_as_a_failed_statement() -> None:
    rubric = _rubric(("a", "must"), ("b", "must"))

    score = to_judge_score(rubric, _verdicts(a=True))

    b = next(r for r in score.results if r.id == "b")
    assert b.passed is False
    assert "no verdict" in b.reason
    assert score.gate is False


def should_ignore_verdicts_for_statements_not_in_the_rubric() -> None:
    rubric = _rubric(("a", "must"))

    score = to_judge_score(rubric, _verdicts(a=True, stray=False))

    assert [r.id for r in score.results] == ["a"]


def should_render_every_rubric_statement_into_the_prompt() -> None:
    prompt = build_judge_prompt(
        narrative="The request was late.",
        summary="Submitted after the window.",
        evidence={"age_days": 47},
        chunks=[],
        rubric=_rubric(("a", "must"), ("b", "should")),
    )

    assert "statement a" in prompt
    assert "statement b" in prompt
    assert "The request was late." in prompt


class _FakeLLM:
    model = "fake-judge"

    def __init__(self, raw: str) -> None:
        self._raw = raw

    async def complete_json(self, **_: Any) -> str:
        return self._raw


@pytest.mark.asyncio
async def should_parse_the_structured_judge_response() -> None:
    client = LLMJudgeClient(
        llm=_FakeLLM('{"results": [{"id": "a", "passed": true, "reason": "ok"}]}')
    )

    verdicts = await client.score_rubric(
        narrative="n",
        summary="s",
        evidence={},
        chunks=[],
        rubric=_rubric(("a", "must")),
    )

    assert verdicts.results[0].id == "a"
    assert verdicts.results[0].passed is True


def should_constrain_judge_output_to_id_passed_reason() -> None:
    item = JUDGE_OUTPUT_SCHEMA["properties"]["results"]["items"]

    assert set(item["required"]) == {"id", "passed", "reason"}
    assert item["additionalProperties"] is False
    assert JUDGE_OUTPUT_SCHEMA["additionalProperties"] is False
