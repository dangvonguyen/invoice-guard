"""Configuration thresholds for deterministic rule evaluation."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.config import Settings


@dataclass(frozen=True)
class RuleConfig:
    """Thresholds the rule checks evaluate extracted fields against."""

    max_expense_amount: Decimal
    max_expense_age_days: int
    allowed_currencies: frozenset[str]
    reconciliation_tolerance: Decimal


def build_rule_config(settings: Settings) -> RuleConfig:
    """Build a `RuleConfig` from application settings."""
    allowed_currencies = frozenset(
        currency.strip().upper()
        for currency in settings.RULE_ALLOWED_CURRENCIES.split(",")
        if currency.strip()
    )
    return RuleConfig(
        max_expense_amount=settings.RULE_MAX_EXPENSE_AMOUNT,
        max_expense_age_days=settings.RULE_MAX_EXPENSE_AGE_DAYS,
        allowed_currencies=allowed_currencies,
        reconciliation_tolerance=settings.RULE_RECONCILIATION_TOLERANCE,
    )
