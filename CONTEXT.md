# Invoice Guard

Expense-invoice intake and review: employees submit invoices, a deterministic rule engine flags policy concerns, and finance reviewers decide.

## Language

**Claim**:
One employee's reimbursement request for a single vendor document, such as a bill, receipt, or itemized statement. A Claim covers one vendor and one document, including its business context and invoice facts.
_Avoid_: Expense report — a rolled-up employee submission that aggregates documents from multiple vendors. This system handles reimbursement at the single-vendor-document level.

**Golden Set**:
A fixed collection of cases paired with hand-verified expected results, used to measure how accurately the system performs one task against ground truth. Each measured task has its own: the Extraction Golden Set and the Explanation Golden Set.
_Avoid_: Test set, eval set (too generic — doesn't convey that the expected values are hand-verified ground truth)

**Extraction Golden Set**:
The Golden Set for invoice-field extraction: invoices paired with the field values a correct extraction should produce.

**Explanation Golden Set**:
The Golden Set for explanation generation: fired Review Flags on Explainable Rules, each paired with the qualities a correct Explanation must have — grounded in the policy handbook and answering that specific flag — since no single wording is the right answer.

**Review Flag**:
One reviewer-visible condition raised when a deterministic rule check fails against an Invoice.
_Avoid_: Exception, violation

**Explainable Rule**:
A rule whose failure can be explained by reference to the active policy handbook, because its threshold is a policy-configured value (e.g. an amount limit, a submission window, an allowed-currency list) rather than a pure data-integrity check (e.g. line items summing to the stated total).
_Avoid_: Policy rule (ambiguous — not all rules are policy-backed)

**Explanation**:
A generated, policy-grounded narrative answering why one Review Flag on an Explainable Rule fired, citing the policy handbook passages it relies on. It reflects the handbook as it stood when it was generated, and is not revised when the handbook is later superseded.
_Avoid_: RAG response

**Citation**:
One policy handbook passage an Explanation references. Always a passage that was actually provided as source material for that Explanation — never one the model recalled on its own.
