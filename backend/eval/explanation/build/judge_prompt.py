"""The judge's static instructions, output schema, and per-case prompt."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.services.explanations.generation import RetrievedChunk
from eval.explanation.build.casefile import Rubric

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
