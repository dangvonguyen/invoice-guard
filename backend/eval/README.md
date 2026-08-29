# Offline evaluation

`eval/` scores production code against a **golden set** — a fixed collection of cases paired with hand-verified expected results. One task is covered today: **invoice-field extraction**.

See the root `CONTEXT.md` for the vocabulary (Golden Set, …) and `docs/adr/0001-extraction-golden-set-scope-and-sourcing.md` for why cases are hand-authored and rendered to PDF rather than sourced from real or synthetic datasets.

## Layout

```
eval/
  paths.py                Filesystem layout, resolved from this package
  extraction/
    build/                Authored source.json -> source.pdf / extracted text / expected.json
    score/                Runs the production ExtractionPipeline over every case and scores it by exact typed comparison
  golden_set/
    extraction/
      cases/              One directory per case (see below)
      schema/expected_invoice.schema.json   Generated from the extraction model
      formats.md          Generated from the template registry
  reports/
    extraction/
      runs/               Per-run debug dumps (git-ignored, local only)
      history.jsonl       One committed line per whole-set scoring run
```

## Running

Both entry points are Python modules; run them from `backend/` so the `eval` and `app` packages import. There are Poe shortcuts:

```sh
poe eval:extract:build      # python -m eval.extraction.build
poe eval:extract:score      # python -m eval.extraction.score
```

`build` needs no credentials. `score` calls a live model, so it needs `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in `backend/.env`.

## The extraction golden set

### Anatomy of a case

Each case is a directory under `golden_set/extraction/cases/`, named `NNN_short_slug`. Two files are authored by hand; three are generated and must never be edited directly:

| File                   | Origin    | Purpose                                                        |
| ---------------------- | --------- | -------------------------------------------------------------- |
| `case.yaml`            | authored  | Title, layout template, dimension tags, label overrides, notes |
| `source.json`          | authored  | The invoice as canonical structured data (`SourceDocument`)    |
| `source.pdf`           | generated | The rendered invoice — what production ingests                 |
| `source.extracted.txt` | generated | `source.pdf` run through the production `PdfTextExtractor`     |
| `expected.json`        | generated | Ground truth, projected from `source.json`                     |

Because `expected.json` is projected from the same authored data that renders the PDF, ground truth cannot silently drift from the document. The projection is near-identity: canonical strings pass through unchanged, the date is already ISO, line items keep their authored order, and the render-only fields (`buyer`, `distractors`) are dropped.

### `case.yaml`

```yaml
title: Classic single-vendor USD invoice with comma-grouped amounts
template: classic-column # required; must be a registered template
dimensions: # closed vocabulary, see build/vocab.py
  - comma-grouped-amount
  - iso-date
label_overrides: # keys must be a subset of LABEL_SLOTS
  tax_amount: Sales Tax
notes: >
  Free-text description of what the case exercises.
```

`dimensions` tags drive the per-dimension slices in a scoring report and the `--dimension` selector. The allowed tags live in `build/vocab.py::DIMENSIONS`.

### `source.json`

Validated against `build/source.py::SourceDocument` at load; unknown keys are rejected. Money is a canonical string (`-?\d+\.\d{2}`), dates are ISO. Key blocks:

- `vendor` / `buyer` — party name, address, contact lines.
- `invoice` — `number`, `date`, `currency`, `tax_amount` (`null` means the document states no tax; `"0.00"` means a zero-tax line is printed), `total_amount`.
- `line_items` — `description`, `amount`, optional `quantity` / `unit_price` (projected), optional `unit` / `vat_rate` (render-only).
- `distractors` — optional ambiguity traps (`po_number`, `bank_account`, `ship_to`); a template must declare the matching slot to place them.
- `render` — data-shaped formatting: `amount_grouping`, `currency_display`, `date_format`.
- `checks` — two arithmetic self-checks. Both default on; a self-check failure aborts build stage.
  - `line_arithmetic`: `quantity * unit_price == amount`
  - `total_reconciliation`: `sum(amounts) + tax == total_amount`

## Build

```sh
python -m eval.extraction.build                            # regenerate every case + schema + formats.md
python -m eval.extraction.build 001_classic_comma_grouped  # one case
python -m eval.extraction.build --emit-schema              # only rewrite the JSON schema
```

For each case it loads `case.yaml` and `source.json`, checks the template can place every optional slot the document uses, renders `source.pdf`, extracts `source.extracted.txt`, runs the self-checks, and writes `expected.json`. A full run also regenerates `schema/expected_invoice.schema.json` (from `ExtractedInvoice`) and `formats.md` (from the template registry).

CI runs the full build stage and then `git diff --exit-code eval`, so a checked-in fixture that no longer matches its source fails the build.

## Score

```sh
python -m eval.extraction.score    # whole set, settings from .env
python -m eval.extraction.score 001_classic_comma_grouped 007_classic_no_invoice_number
python -m eval.extraction.score --dimension itemized-vat --dimension zero-tax
python -m eval.extraction.score --provider anthropic --model claude-... --max-tokens 4096 --concurrency 8
```

The harness loads the selected cases, drives the real `ExtractionPipeline` over each `source.extracted.txt` concurrently, and compares the result to `expected.json` with exact, typed equality — no fuzzy matching. Positional case names and `--dimension` are mutually exclusive.

What it measures, per run and per dimension tag:

- **Fully-correct rate** — cases where every scalar field and the ordered line-item list match.
- **Error rate** — cases where the pipeline raised (a measured outcome).
- **Field accuracy** — a `correct / total` tally for each scalar field (`vendor_name`, `invoice_number`, `invoice_date`, `currency`, `tax_amount`, `total_amount`) and for `line_items_ordered`, `line_items_unordered`, and `line_item_fields` (the four subfields across all rows).

A provider authentication or connection error aborts the run before any artifact is written; a per-case pipeline exception is recorded as an errored case.

### Artifacts

- `reports/extraction/runs/<timestamp>_<provider>_<model>.json` — the full per-case dump for one run (`schema_version: 1`). Git-ignored; a local debugging aid.
- `reports/extraction/history.jsonl` — one compact line per **whole-set** run (`v: 1`), committed, so accuracy over time is visible in the diff. Selective runs (case names or `--dimension`) do not append a history line.
