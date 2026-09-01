---
status: "accepted"
date: 2026-08-31
---

# Explanation golden set: scope and scoring

## Context and Problem Statement

The Explanation Golden Set measures explanation generation for fired Review Flags on Explainable Rules: given one flag and the policy passages retrieval would have surfaced, is the generated narrative-plus-citations grounded in those passages and does it answer that specific flag? There is no single correct wording, and the explanation under test is produced by a live model, so no score is a fixed value. What should a case hold, and how is a free-text answer graded?

## Decision Drivers

- No reference string is "the" answer; correctness is a set of qualities, not a string match.
- The explanation under test comes from a non-deterministic model, so a rate already moves run to run; the grader should not add more moving parts than it must.
- Where a handbook is silent on a rule, declining to answer is the correct behaviour and must be gradeable, not skipped.
- Retrieval is a separate concern and stays out of this set.

## Considered Options

- Exact-match against a canonical reference explanation
- An LLM judge alone, against a per-case rubric
- Mechanical checks on the objective parts, plus an LLM judge for the rest
- End-to-end retrieval-plus-generation scoring

## Decision Outcome

Chosen option: **mechanical checks plus an LLM judge**, because it keeps a judge-free signal on what is objectively checkable while still putting a number on the qualities a check cannot express.

- Each case is graded in isolation: it fixes the flag, its evidence, and the ordered passage set that stands in for retrieval, then grades one generated answer.
- Mechanical checks cover what is objective: which of the offered passages were cited, against a per-case expectation with a tolerance, and the presence or absence of required terms.
- The judge covers what has no mechanical form: whether every claim is grounded in the offered passages, whether the answer addresses this specific flag, and whether it declines when the passages do not support an answer.
- A case passes fully only when both layers pass; the mechanical layer is also reported on its own.
- Where the handbook states no such rule, the expected answer cites nothing and says so; these cases are first-class, not skipped.
- Scoring is informational — a reported trend, never a merge gate.

### Consequences

- Good, because the mechanical layer is judge-free: no second model, and it does not move when the judge model changes.
- Good, because grading runs production's real generation path, so a prompt or output-contract regression shows up here.
- Good, because abstention is a graded outcome, not an untested gap.
- Bad, because the mechanical layer is loose — a fluent, well-cited answer that says nothing still passes it; only the judge catches that, and the judge's verdict is itself non-deterministic and model-dependent.
- Bad, because no rate here is stable: every one grades a fresh generation, and the fuller verdict also shifts with the judge model, so a real regression has to clear that noise.
- Bad, because generation-only scope leaves retrieval untested, and each case's passage set is assumed correct rather than checked against the live rules or a real retriever.
- Bad, because a case can only draw on policy the handbook actually contains: a production failure that turns on a rule the handbook is silent about can only be reproduced here as an abstention case, not as a grounded explanation.

## Pros and Cons of the Options

### Mechanical checks plus an LLM judge

- Good, because it gives a judge-free signal on the objective parts plus coverage of the qualities no check can express.
- Bad, because it is two graders to maintain: the cheap one is loose, the thorough one is non-deterministic.

### Exact-match against a canonical reference explanation

- Good, because the grading step is mechanical and needs no judge.
- Bad, because there is no single correct wording, so it measures conformance to one arbitrary phrasing, and against a non-deterministic generator it would almost never match.

### An LLM judge alone

- Good, because it is the simplest to author and run, and it targets the qualities that matter.
- Bad, because every number then depends on a non-deterministic, model-specific call, with nothing checkable without it.

### End-to-end retrieval-plus-generation scoring

- Good, because it measures the outcome a reviewer actually sees, retrieval mistakes included.
- Bad, because it folds retrieval into the score and makes a generation regression hard to isolate.

## More Information

Sibling of [ADR 0001](0001-extraction-golden-set-scope-and-sourcing.md). Both sets grade a task against hand-verified expectations and regenerate their fixtures deterministically, but measure different tasks. Domain terms (Golden Set, Explanation, Citation, Explainable Rule, Review Flag) are defined in `CONTEXT.md`.
