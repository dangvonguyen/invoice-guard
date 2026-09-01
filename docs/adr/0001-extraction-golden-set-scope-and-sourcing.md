---
status: "accepted"
date: 2026-08-29
---

# Extraction golden set: scope and fixture sourcing

## Context and Problem Statement

The Extraction Golden Set measures how accurately invoice-field extraction matches hand-verified ground truth. It needs fixtures that resemble what production ingests — a PDF in, extracted text out — carry expected values a reviewer can trust, and span enough formatting variety to exercise the extractor. Text-native invoice datasets with hand-verified ground truth are effectively unavailable. Where do the fixtures come from, and how is ground truth kept from drifting away from the document it describes?

## Decision Drivers

- Ground truth must not drift from the document it describes.
- Fixtures must resemble production input (PDF rendered, text extracted).
- Formatting diversity — number/date/currency forms, label vocabulary, structural ordering, ambiguity traps — must scale without near-duplicate documents.

## Considered Options

- Hand-authored structured data, rendered to PDF by a committed generator
- Real anonymized invoices
- Multi-vendor expense-report datasets
- A bundled synthetic invoice-PDF dataset
- Literal Markdown source plus hand-written expected fields
- Hand-authored text fed straight to the pipeline, skipping PDF rendering

## Decision Outcome

Chosen option: **hand-authored structured data, rendered to PDF by a committed generator**, because it is the only option that keeps ground truth mechanically tied to the document while still producing real PDF input and open-ended formatting variety.

- Each case is authored as structured data that names a layout template.
- A generator renders the case to a PDF and runs production's extractor over it; the expected fields are derived from the authored data.
- That derivation is near-identity — values are authored in canonical form and formatted only when rendered — so ground truth cannot disagree with the document.
- Diversity comes from one dataset spanning many templates, varying the axes that change the extracted text.

### Consequences

- Good, because ground truth is verifiable in the diff and cannot silently diverge from the rendered document.
- Good, because new formatting coverage is a new template, not a new hand-copied document.
- Bad, because every fixture depends on the generator and its templates; a template bug can invalidate a batch of cases at once.
- Bad, because fixtures are synthetic, so real-world quirks no template anticipates are absent until someone adds them.

## Pros and Cons of the Options

### Hand-authored structured data, rendered to PDF by a committed generator

- Good, because expected fields are derived from the authored data and reviewable in the diff, so ground truth can't drift.
- Good, because diversity scales through templates rather than near-duplicate documents.
- Bad, because the fixture corpus is only as realistic as its templates.

### Real anonymized invoices

- Bad, because text-native datasets with hand-verified ground truth are effectively unavailable; what exists is image-only or JSON-only.

### Multi-vendor expense-report datasets

- Bad, because they don't fit the extractor's single-vendor model (see `CONTEXT.md`) and would need invented ground truth for absent fields.

### A bundled synthetic invoice-PDF dataset

- Bad, because the usable sample was one fixed template supplying no diversity, and mixing it with hand-authored fixtures blurred provenance for no gain.

### Literal Markdown source plus hand-written expected fields

- Bad, because it scales badly to formatting diversity and hand-copying invites drift between document and ground truth.

### Hand-authored text fed straight to the pipeline, skipping PDF rendering

- Bad, because with no real PDFs in the set, the text-extraction step is the only thing keeping fixtures honest about production input.

## More Information

Sibling of [ADR 0002](0002-explanation-golden-set-scope-and-scoring.md), which covers the Explanation Golden Set's scope and scoring. Both sets share the `eval/` tooling and the diff-gate discipline but measure different tasks.
