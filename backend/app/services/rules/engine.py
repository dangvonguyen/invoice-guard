"""Evaluate an extracted invoice against every configured deterministic rule."""

from datetime import date

from app.services.extraction.model import ExtractedInvoice
from app.services.rules.config import RuleConfig
from app.services.rules.definitions import RULES, RuleDefinition
from app.services.rules.result import RuleResult


class RuleEngine:
    """Evaluate an invoice against the full, fixed set of configured rules."""

    def __init__(
        self, *, config: RuleConfig, rules: tuple[RuleDefinition, ...] = RULES
    ) -> None:
        self._config = config
        self._rules = rules

    def evaluate(
        self, extracted_invoice: ExtractedInvoice, today: date
    ) -> list[RuleResult]:
        """Return one `RuleResult` per configured rule, in a stable order."""
        return [
            rule.check(extracted_invoice, self._config, today) for rule in self._rules
        ]
