"""Check whether an extracted value is traceable to its source document.

A value the model invents that never appears in the parsed source text is
flagged low-confidence independently of the model's own confidence claim
"""

from datetime import date
from decimal import Decimal


class GroundingChecker:
    """Decide whether a value is grounded in a document's source text."""

    def is_grounded(self, value: str | date | Decimal, source_text: str) -> bool:
        """Return whether `value` appears in `source_text`."""
        return any(self._matches(c, source_text) for c in self._candidates(value))

    def _matches(self, value: str, source_text: str) -> bool:
        return self._normalize(value) in self._normalize(source_text)

    @staticmethod
    def _candidates(value: str | date | Decimal) -> tuple[str, ...]:
        candidates: tuple[str, ...]
        if isinstance(value, date):
            year, month, day = value.year, value.month, value.day
            candidates = (
                f"{year:04d}-{month:02d}-{day:02d}",
                f"{month:02d}/{day:02d}/{year:04d}",
                f"{month}/{day}/{year:04d}",
                f"{day:02d}/{month:02d}/{year:04d}",
                f"{day}/{month}/{year:04d}",
            )
        elif isinstance(value, Decimal):
            candidates = (
                format(value, "f"),
                format(value, ",f"),
            )
        else:
            candidates = (value,)
        return tuple(dict.fromkeys(candidates))

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.split()).lower()
