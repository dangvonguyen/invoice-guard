"""Frozen vocab the explanation build and case loader pin against production.

Hard-coded rather than sourced from ``get_settings()``: the build must stay
keyless and the committed ``chunks.json`` must not depend on the environment.
``test_constants.py`` guards each value against its production counterpart, so
drift is caught in tests, not silently in the build.
"""

from app.services.rules.result import RuleCode

# Section-chunker params. Equal to the production ingestion defaults
# (``POLICY_CHUNK_MIN_TOKENS`` / ``POLICY_CHUNK_MAX_TOKENS``).
CHUNKER: dict[str, int] = {"min_tokens": 100, "max_tokens": 500}

# The evidence keys each explainable rule's check emits on FAIL
EVIDENCE_KEYS: dict[RuleCode, frozenset[str]] = {
    RuleCode.EXPENSE_WITHIN_AMOUNT_LIMIT: frozenset(
        {"invoice_total", "max_expense_amount", "currency"}
    ),
    RuleCode.EXPENSE_WITHIN_SUBMISSION_WINDOW: frozenset(
        {"invoice_age_days", "max_expense_age_days"}
    ),
    RuleCode.CURRENCY_ALLOWED: frozenset({"currency", "allowed_currencies"}),
}

# Closed dimension vocabulary, every case carries at least one
DIMENSIONS: frozenset[str] = frozenset(
    {
        "clean-passage",
        "threshold-in-prose",
        "conditional-limit",
        "cross-referenced",
        "distractor-heavy",
        "hard-negative",
        "wrong-number-distractor",
    }
)
