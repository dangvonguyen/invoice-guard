"""Check whether an extracted value is traceable to its source document.

A value the model invents that never appears in the parsed source text is
flagged low-confidence independently of the model's own confidence claim
"""


class SpanGroundingChecker:
    """Decide whether a value is grounded in a document's source text."""

    def check(self, *, value: str, source_text: str) -> bool:
        """Return whether `value` appears in `source_text`."""
        return self._normalize(value) in self._normalize(source_text)

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.split()).lower()
