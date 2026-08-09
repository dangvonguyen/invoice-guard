"""Structured JSON logging with per-request correlation."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

_UNSTRUCTURED_EVENT = "log.unstructured"


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

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
            "event": getattr(record, "event", _UNSTRUCTURED_EVENT),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", None),
            "context": context,
        }
        return json.dumps(payload, default=str)
