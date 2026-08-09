"""Structured JSON logging with per-request correlation."""

import json
import logging
from collections.abc import Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_DISABLED_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
)
_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_USER_ID: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_request_id() -> str:
    """Return the request ID bound to the current execution context, if any."""
    return _REQUEST_ID.get()


def bind_request_id(request_id: str | None) -> None:
    """Bind (or clear) the request ID for the current execution context."""
    if request_id is None:
        _REQUEST_ID.set("-")
    else:
        _REQUEST_ID.set(request_id)


def get_user_id() -> str | None:
    """Return the user ID bound to the current execution context, if any."""
    return _USER_ID.get()


def bind_user_id(user_id: str | None) -> None:
    """Bind (or clear) the user ID for the current execution context."""
    _USER_ID.set(user_id)


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

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a JSON string."""
        context: dict[str, Any] = dict(getattr(record, "context", {}) or {})
        if record.exc_info:
            context["exception"] = self.formatException(record.exc_info)

        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
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
    def _redact(cls, value: Any) -> Any:
        """Recursively copy a value, masking data under sensitive-looking keys."""
        if isinstance(value, Mapping):
            return {
                key: (
                    cls.REDACTED_VALUE
                    if isinstance(key, str) and cls._should_redact(key)
                    else cls._redact(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._redact(item) for item in value)
        if isinstance(value, set):
            return {cls._redact(item) for item in value}
        if isinstance(value, frozenset):
            return frozenset(cls._redact(item) for item in value)
        return value


class ContextVarLogFilter(logging.Filter):
    """Attach request_id/user_id from the current context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True


def configure_logging(level: int | str = logging.INFO) -> None:
    """Configure the root logger and bridge known third-party loggers into it."""
    handler = logging.StreamHandler()
    handler.addFilter(ContextVarLogFilter())
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Custom middleware already logs one structured line per request, so
    # silence other loggers rather than rerouted through the JSON handler.
    for name in _DISABLED_LOGGERS:
        logging.getLogger(name).disabled = True
