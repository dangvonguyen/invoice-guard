# Golden-set scope and fixture sourcing

The golden set scores extraction accuracy only — it does not assert rule-engine outcomes (already covered by deterministic unit tests against fixed `ExtractedInvoice` fixtures) or explanation-generation quality (a narrative/citation judgment that needs a fundamentally different measurement approach, e.g. an LLM-as-judge rubric, not field-level exact-match). Bundling either into the same harness would blur two different eval methodologies and make failures ambiguous about which layer broke.

Fixtures are a deliberate mix: a handful of invoices from the Kaggle "High-Quality OCR-Ready Invoice PDFs" dataset (Apache 2.0, fully synthetic, no real transaction data), which supplied real evidence for two schema decisions, plus hand-authored cases for formatting diversity the dataset doesn't cover (other currencies, zero-tax invoices, ambiguous date formats, symbol/comma-formatted amounts, a service invoice with no quantity, unusual vendor-name punctuation).

## Considered Options

- Real anonymized invoices sourced independently — rejected: text-native (non-image) real invoice datasets with hand-verified ground truth are effectively unavailable publicly; what's findable is either image-only or JSON-only.
- Multi-vendor expense-report-style datasets encountered during that search — rejected: doesn't fit `ExtractedInvoice`'s single-vendor model (see `CONTEXT.md`'s `Invoice` entry); would require inventing ground truth for fields (e.g. `vendor_name`) the document doesn't unambiguously have.
