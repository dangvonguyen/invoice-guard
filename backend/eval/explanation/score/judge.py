"""The LLM judge: one structured call per case, scoring the narrative against the
case's rubric statements.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.config import ModelProvider
from app.core.llm import StructuredLLM, build_structured_llm
from app.services.explanations.generation import RetrievedChunk
from eval.explanation.build.casefile import Rubric
from eval.explanation.score.results import JudgeResult, JudgeScore

JUDGE_INSTRUCTIONS = (
    "You are grading one explanation written for an invoice-review flag. You are "
    "given the flag summary, the structured evidence, the numbered policy "
    "excerpts the writer was shown, the explanation itself, and a list of rubric "
    "statements. For each rubric statement, decide whether the explanation "
    "satisfies it, judging only against the evidence and excerpts provided and "
    "never against outside knowledge. Return exactly one verdict per statement, "
    "preserving its id, each with a one-sentence reason. Mark a statement passed "
    "only when it is clearly satisfied; when in doubt, fail it."
)

JUDGE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "passed", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

_MISSING_VERDICT_REASON = "judge returned no verdict for this statement"


class JudgeVerdict(BaseModel):
    """The judge's raw call on one rubric statement."""

    id: str
    passed: bool
    reason: str


class JudgeVerdicts(BaseModel):
    """The judge's full structured response: one verdict per rubric statement."""

    results: list[JudgeVerdict]


class JudgeClient(Protocol):
    """Call the judge model and return a verdict per rubric statement."""

    @property
    def model(self) -> str: ...

    async def score_rubric(
        self,
        *,
        narrative: str,
        summary: str,
        evidence: Mapping[str, Any],
        chunks: Sequence[RetrievedChunk],
        rubric: Sequence[Rubric],
    ) -> JudgeVerdicts:
        """Judge ``narrative`` against every ``rubric`` statement."""
        ...


def build_judge_prompt(
    *,
    narrative: str,
    summary: str,
    evidence: Mapping[str, Any],
    chunks: Sequence[RetrievedChunk],
    rubric: Sequence[Rubric],
) -> str:
    """The exact user message the judge model receives for one case."""
    excerpts = "\n\n".join(
        f"[{index}] {chunk.section_label or 'Untitled section'}: {chunk.content}"
        for index, chunk in enumerate(chunks)
    )
    statements = "\n".join(f"- {item.id}: {item.statement}" for item in rubric)
    return (
        f"Review flag: {summary}\n"
        f"Evidence: {dict(evidence)}\n\n"
        f"Policy excerpts:\n{excerpts}\n\n"
        f"Explanation under review:\n{narrative}\n\n"
        f"Rubric statements:\n{statements}"
    )


class LLMJudgeClient:
    """`JudgeClient` backed by a structured-output LLM."""

    def __init__(self, *, llm: StructuredLLM) -> None:
        self._llm = llm

    @property
    def model(self) -> str:
        return self._llm.model

    async def score_rubric(
        self,
        *,
        narrative: str,
        summary: str,
        evidence: Mapping[str, Any],
        chunks: Sequence[RetrievedChunk],
        rubric: Sequence[Rubric],
    ) -> JudgeVerdicts:
        raw = await self._llm.complete_json(
            instructions=JUDGE_INSTRUCTIONS,
            schema=JUDGE_OUTPUT_SCHEMA,
            schema_name="explanation_rubric_verdicts",
            user_message=build_judge_prompt(
                narrative=narrative,
                summary=summary,
                evidence=evidence,
                chunks=chunks,
                rubric=rubric,
            ),
        )
        return JudgeVerdicts.model_validate_json(raw)


def build_judge_client(
    *, provider: ModelProvider, model: str, max_tokens: int
) -> JudgeClient:
    """Return the `JudgeClient` for the configured judge provider."""
    return LLMJudgeClient(
        llm=build_structured_llm(provider=provider, model=model, max_tokens=max_tokens)
    )


def to_judge_score(rubric: Sequence[Rubric], verdicts: JudgeVerdicts) -> JudgeScore:
    """Map the judge's verdicts back onto the rubric."""
    by_id = {verdict.id: verdict for verdict in verdicts.results}
    results = [
        JudgeResult(
            id=item.id,
            severity=item.severity,
            passed=by_id[item.id].passed if item.id in by_id else False,
            reason=(
                by_id[item.id].reason if item.id in by_id else _MISSING_VERDICT_REASON
            ),
        )
        for item in rubric
    ]
    return JudgeScore(results=results)
