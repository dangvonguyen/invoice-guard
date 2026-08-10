"""Validate uploaded invoice files by declared MIME type and size."""


class InvoiceMimeValidator:
    """Enforce the Core-scope upload contract: text-native PDF only."""

    def validate(
        self, *, filename: str | None, content_type: str | None, size: int | None
    ) -> None:
        """Accept a supported invoice document."""
