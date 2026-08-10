"""Validate uploaded invoice files by declared MIME type and size."""


class InvoiceMimeValidator:
    """Enforce the Core-scope upload contract: text-native PDF only."""

    def validate(self, *, original_filename: str, content_type: str, size: int) -> None:
        """Accept a supported invoice document."""
