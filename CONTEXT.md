# Invoice Guard

Expense-invoice intake and review: employees submit invoices, a deterministic rule engine flags policy concerns, and finance reviewers decide.

## Language

**Invoice**:
One document from a single vendor for a single transaction — a bill, receipt, or itemized statement — that an employee submits for reimbursement or payment. Its line items, tax, and total all belong to that one vendor.
_Avoid_: Expense claim, expense report (a different, unsupported concept — an employee's rolled-up submission aggregating receipts from many vendors into one reimbursement payout; this system extracts and reviews at the single-vendor-document level, not the aggregated-report level)

**Golden Set**:
A fixed collection of invoice documents paired with hand-verified expected extraction results, used to measure extraction accuracy against ground truth.
_Avoid_: Test set, eval set (too generic — doesn't convey that the expected values are hand-verified ground truth)

**Review Flag**:
One reviewer-visible condition raised by a `FAIL` outcome from a deterministic rule check against an invoice.
_Avoid_: Exception, violation

**Explainable Rule**:
A rule whose failure may be explained by retrieving and citing the active policy handbook, because its threshold is a policy-configured value (e.g. an amount limit, a submission window, an allowed-currency list) rather than a pure data-integrity check (e.g. line items summing to the stated total).
_Avoid_: Policy rule (ambiguous — not all rules are policy-backed)

**Explanation**:
A generated, policy-grounded narrative answering why one review flag on an explainable rule fired, produced on demand by retrieving relevant policy handbook chunks and citing them. Cached once generated; not regenerated when the policy handbook is later superseded.
_Avoid_: RAG response

**Citation**:
One policy handbook chunk an explanation references, drawn only from the chunks actually retrieved for that explanation — never a chunk the model merely recalls without it being retrieved.
