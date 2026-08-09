"""Structured JSON logging with per-request correlation."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    UNSTRUCTURED_EVENT = "log.unstructured"
    DENYLIST_SUBSTRING = (
        "password",
        "secret",
        "token",
        "authorization",
        "jwt",
    )
    REDACTED_VALUE = "[REDACTED]"

    def __init__(self, schema_version: int = 1):
        super().__init__()
        self._schema_version = schema_version

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a JSON string."""
        context: dict[str, Any] = dict(getattr(record, "context", {}) or {})
        if record.exc_info:
            context["exception"] = self.formatException(record.exc_info)

        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "schema_version": self._schema_version,
            "level": record.levelname,
            "event": getattr(record, "event", self.UNSTRUCTURED_EVENT),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", None),
            "context": self._redact(context),
        }
        return json.dumps(payload, default=str)

    @classmethod
    def _should_redact(cls, key: str) -> bool:
        """Return whether a context key appears to contain sensitive data."""
        return any(marker in key.lower() for marker in cls.DENYLIST_SUBSTRING)

    @classmethod
    def _redact(cls, context: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of context with sensitive-looking keys masked."""
        return {
            key: cls.REDACTED_VALUE if cls._should_redact(key) else value
            for key, value in context.items()
        }
