# Offline evaluation

`eval/` scores production code against a **golden set** — fixed cases paired with hand-verified expected results. Two tasks are covered:

- **Invoice-field extraction** — invoices paired with the fields a correct extraction should produce.
- **Explanation generation** — fired Review Flags on Explainable Rules, paired with the qualities a correct Explanation must have.

Vocabulary is in the root `CONTEXT.md`; why each task's cases are shaped as they are is argued in ADRs 0001 and 0002.

## Layout

```
eval/
  _common/            Shared paths and scoring-harness helpers
  extraction/
    build/            Authored source.json -> source.pdf / extracted text / expected.json
    score/            Runs the production ExtractionPipeline, scores by exact typed comparison
  explanation/
    build/            Handbook PDF -> handbook.md / chunks.json + per-case prompt.txt + fixtures
    score/            Runs production generation, scores with deterministic checks plus an LLM judge
  golden_set/
    handbook/         Source policy PDFs, byte-for-byte, with provenance (shared)
    extraction/       cases/ + generated schema/ and formats.md
    explanation/      cases/ + generated handbook/, prompt/, schema/
  reports/
    <task>/
      runs/           Per-run debug dumps (git-ignored)
      history.jsonl   One committed line per whole-set run
```

## How both tasks work

Run from `backend/`. Poe shortcuts:

```sh
poe eval:extract:build      # python -m eval.extraction.build
poe eval:extract:score      # python -m eval.extraction.score
poe eval:explain:build      # python -m eval.explanation.build
poe eval:explain:score      # python -m eval.explanation.score
poe eval:build              # both build stages, in sequence
poe eval:score              # both score stages, in sequence
```

**Cases.** One directory per case under `golden_set/<task>/cases/`, named `NNN_short_slug`. Some files are authored; the rest are generated and must not be edited.

**Build** (`python -m eval.<task>.build`) regenerates the generated fixtures offline, with no credentials. CI runs it then `git diff --exit-code eval`, so a stale fixture fails the build.

**Score** (`python -m eval.<task>.score`) calls live models, so it needs API keys in `backend/.env`; it is informational only, never a merge gate. Common options: positional case names or `--dimension TAG` (repeatable) to select a subset — the two are mutually exclusive — and `--provider` / `--model` / `--max-tokens` / `--concurrency` overrides. Metrics are reported per run and per dimension tag. An auth or connection error aborts the run before any artifact is written; a per-case failure is recorded as an errored case.

**Artifacts** under `reports/<task>/`:

- `runs/<timestamp>_<provider>_<model>.json` — the full per-case dump, git-ignored, a local debugging aid.
- `history.jsonl` — one compact line per **whole-set** run, committed, so the trend shows in the diff. Selective runs do not append.

## The extraction golden set

### A case

`case.yaml` and `source.json` are authored; the rendered invoice PDF, its extracted text, and the expected field values are generated. The expected values are projected from the same authored data that renders the PDF, so ground truth cannot drift from the document.

```yaml
title: Classic single-vendor USD invoice with comma-grouped amounts
template: classic-column # required; a registered template
dimensions: # closed vocabulary, see build/vocab.py::DIMENSIONS
  - comma-grouped-amount
  - iso-date
label_overrides: # keys a subset of LABEL_SLOTS
  tax_amount: Sales Tax
notes: >
  Free-text description of what the case exercises.
```

`source.json` is validated against `build/source.py::SourceDocument`; unknown keys are rejected. Money is `-?\d+\.\d{2}`, dates are ISO. Blocks: `vendor` / `buyer`, `invoice` (`number`, `date`, `currency`, `tax_amount`, `total_amount`), `line_items`, optional `distractors` (ambiguity traps), `render` (formatting), and two `checks` self-checks (`line_arithmetic`, `total_reconciliation`) that abort the build on mismatch.

### Build

```sh
python -m eval.extraction.build                            # every case + schema + formats.md
python -m eval.extraction.build 001_classic_comma_grouped  # one case
python -m eval.extraction.build --emit-schema              # only the JSON schema
```

Per case: load `case.yaml` + `source.json`, check the template can place every slot used, render `source.pdf`, extract text `source.extracted.txt`, run the self-checks, write `expected.json`. A full run also regenerates `schema/expected_invoice.schema.json` and `formats.md`.

### Score

```sh
python -m eval.extraction.score    # whole set, settings from .env
python -m eval.extraction.score 001_classic_comma_grouped 007_classic_no_invoice_number
python -m eval.extraction.score --dimension itemized-vat --dimension zero-tax
python -m eval.extraction.score --provider anthropic --model claude-... --max-tokens 4096 --concurrency 8
```

Drives the production extraction pipeline over each case's extracted text and compares the result to `expected.json` with exact typed equality. Measures:

- **Fully-correct rate** — every scalar field and the ordered line-item list match.
- **Error rate** — the pipeline raised (a measured outcome).
- **Field accuracy** — `correct / total` per scalar field and for `line_items_ordered` / `line_items_unordered` / `line_item_fields`.

## The explanation golden set

Each case fixes one fired flag, its evidence, and an ordered passage set that stands in for retrieval, then grades one freshly generated Explanation. Retrieval is out of scope — the passage set is authored. See ADR 0002.

### A case

`case.yaml` is authored; `prompt.txt` (the exact user message production would send) is generated.

```yaml
title: Reimbursement request filed 47 days after the event
rule: EXPENSE_WITHIN_SUBMISSION_WINDOW # a RuleCode; an Explainable Rule with a FAIL summary
dimensions: # closed vocabulary, see build/constants.py::DIMENSIONS
  - clean-passage
evidence: # keys must equal this rule's contract in build/constants.py::EVIDENCE_KEYS
  invoice_age_days: 47
  max_expense_age_days: 30
context: # ordered chunk IDs from handbook/chunks.json — what the model is shown
  - "2. Lodging#0"
  - "6. Expense Reimbursement Timelines#0"
grading:
  citations:
    ideal: ["6. Expense Reimbursement Timelines#0"] # a subset of context
    min_recall: 1.0 # fraction of ideal that must be cited
    max_spurious: 0 # cited-but-not-ideal chunks tolerated
  checks: # deterministic regex over the narrative
    - id: names_window
      kind: must_contain # or must_absent
      pattern: '30\s*days'
  rubric: # judge-scored statements
    - id: answers_this_flag
      severity: must # every `must` gates the judge; `should` is reported only
      statement: Attributes the flag to the request being filed more than 30 days after the event.
```

A hard-negative case — one the handbook has no rule for — carries the `hard-negative` tag **and** an empty `citations.ideal`; the correct answer cites nothing and says so.

`handbook/chunks.json` is the handbook run through the production section chunker with the same size limits ingestion uses, pinned here so the split can't move underneath the cases. Each chunk's ID is its section heading plus an ordinal; `handbook/SOURCE.md` records how the current handbook split.

### Build

```sh
python -m eval.explanation.build   # no arguments
```

Regenerates `handbook/handbook.md` (verbatim text-extractor output), `handbook/chunks.json`, the static `prompt/` and `schema/` fixtures (production generation and judge instructions and output schemas), and each `cases/*/prompt.txt`. Validation aborts on: an unknown dimension, evidence keys off the rule contract, a `context` ID absent from the handbook, duplicate `context` IDs, an `ideal` citation outside `context`, an ID reused across `checks` and `rubric`, a `hard-negative` tag without an empty `ideal` (or vice versa), a non-explainable rule or one with no FAIL summary, or a chunk-ID collision.

### Score

```sh
python -m eval.explanation.score 001_submission_window_overdue 007_amount_limit_hard_negative
python -m eval.explanation.score --dimension hard-negative
python -m eval.explanation.score --judge-provider openai --judge-model gpt-...
```

Calls the production generation client directly over each case's flag + evidence + context, then grades in two layers. Generation settings come from `GENERATION_*`; judge settings default to them unless `JUDGE_*` (env or `--judge-*` flag) override.

**Deterministic layer** (keyless):

- **Citation gate** — the passages the model cited are mapped back onto `context`; recall over the `ideal` set must clear `min_recall`, spurious citations must stay within `max_spurious`, and no index may fall out of range.
- **Check gate** — every `must_contain` / `must_absent` phrase check holds.
- The deterministic verdict is both gates passing.

**Judge layer** — one structured LLM call per case returns a verdict per rubric statement. It passes only when every `must` statement passes; `should` statements are tallied but don't gate.

A case fully passes only when the deterministic verdict and the judge agree. Measures: deterministic-pass / full-pass / error rate, mean citation recall / precision, spurious rate, out-of-range rate, and a pass tally per check and per `must` / `should` statement. `history.jsonl` also carries the judge provider/model.
