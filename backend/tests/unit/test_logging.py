"""Specify structured JSON logging and request-id correlation behavior."""

import json
import logging
import sys
from typing import Any

import pytest

from app.core.logging import JsonFormatter

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def formatter() -> JsonFormatter:
    """Provide a default JSON formatter for each test."""
    return JsonFormatter()


def make_record(
    message: str = "test",
    level: int = logging.INFO,
    exc_info: Any | None = None,
    **extra: object,
) -> logging.LogRecord:
    """Build a bare LogRecord for formatter tests without a live logger."""
    record = logging.LogRecord(
        name="app.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def should_include_required_fields(formatter: JsonFormatter) -> None:
    """Produce a unified view for every record."""
    payload = json.loads(formatter.format(make_record()))

    assert set(payload) == {
        "timestamp",
        "level",
        "event",
        "message",
        "request_id",
        "user_id",
        "context",
    }


def should_default_missing_event_to_unstructured_marker(
    formatter: JsonFormatter,
) -> None:
    """Never raise or emit null for event; fall back to a stable marker."""
    payload = json.loads(formatter.format(make_record()))

    assert payload["event"] == "log.unstructured"


def should_carry_event_and_context_from_record_extras(
    formatter: JsonFormatter,
) -> None:
    """Surface extra['event'] and extra['context'] into the record."""
    record = make_record(
        event="http.request.completed",
        context={"status_code": 200, "duration_ms": 12.3},
        request_id="req_1",
    )

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "http.request.completed"
    assert payload["context"] == {"status_code": 200, "duration_ms": 12.3}


def should_include_exception_traceback_under_context_when_present(
    formatter: JsonFormatter,
) -> None:
    """Nest exception info under context, not as a top-level field."""
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = make_record(context={}, exc_info=sys.exc_info())

    payload = json.loads(formatter.format(record))

    assert "RuntimeError: boom" in payload["context"]["exception"]


@pytest.mark.parametrize(
    "key",
    ["password", "hashed_password", "access_token", "Authorization", "JWT_SECRET_KEY"],
)
def should_redact_known_sensitive_keys_case_insensitively(
    formatter: JsonFormatter, key: str
) -> None:
    """Replace the value of any denylisted key regardless of casing."""
    record = make_record(context={key: "sensitive-data"})

    payload = json.loads(formatter.format(record))

    assert payload["context"] == {key: "[REDACTED]"}


def should_leave_non_sensitive_keys_unchanged(formatter: JsonFormatter) -> None:
    """Pass through keys not on the denylist without modification."""
    record = make_record(context={"duration_ms": "12.3", "status_code": 429})

    payload = json.loads(formatter.format(record))

    assert payload["context"] == {"duration_ms": "12.3", "status_code": 429}


def should_not_mutate_the_input_dict(formatter: JsonFormatter) -> None:
    """Return a new dict rather than mutating the caller's context."""
    original = {"password": "secret"}
    record = make_record(context=original)

    formatter.format(record)

    assert original == {"password": "secret"}
