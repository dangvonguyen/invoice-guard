"""Tests for request correlation and structured HTTP logging."""

import logging
from collections.abc import Awaitable, Callable, Iterator
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.api.middleware import RequestLoggingMiddleware
from app.core.logging import ContextVarLogFilter, bind_user_id, get_request_id

pytestmark = pytest.mark.unit


class StructuredLogRecord(logging.LogRecord):
    """Log record fields added by the structured logging stack."""

    event: str
    user_id: str | None
    context: dict[str, Any]


class ListHandler(logging.Handler):
    """Collect structured log records for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[StructuredLogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(cast(StructuredLogRecord, record))


@pytest.fixture
def captured_http_logs() -> Iterator[ListHandler]:
    """Capture records emitted by the dedicated HTTP request logger."""
    handler = ListHandler()
    handler.addFilter(ContextVarLogFilter())
    logger = logging.getLogger("app.api.middleware")
    original_level = logger.level
    original_propagate = logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        logger.propagate = original_propagate


def client(endpoint: Callable[[Request], Awaitable[Response]]) -> AsyncClient:
    """Build an in-process client around one middleware-wrapped endpoint."""
    app = Starlette(routes=[Route("/x", endpoint, methods=["POST"])])
    app.add_middleware(RequestLoggingMiddleware)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def record_for(handler: ListHandler, event: str) -> StructuredLogRecord:
    """Return the single captured record for an event."""
    [record] = [item for item in handler.records if item.event == event]
    return record


@pytest.mark.asyncio
async def should_surface_user_id_bound_in_handler_on_completion_log(
    captured_http_logs: ListHandler,
) -> None:
    """Include the authenticated user ID bound by the downstream handler."""

    async def endpoint(_: Request) -> Response:
        bind_user_id("u-482")
        return JSONResponse({"ok": True}, status_code=200)

    async with client(endpoint) as c:
        await c.post("/x")

    record = record_for(captured_http_logs, "http.request.completed")
    assert record.user_id == "u-482"


@pytest.mark.asyncio
async def should_set_request_id_response_header_and_bind_it_downstream() -> None:
    """Expose the same generated request ID to the handler and response client."""
    seen: dict[str, str] = {}

    async def endpoint(_: Request) -> Response:
        seen["request_id"] = get_request_id()
        return JSONResponse({"ok": True})

    async with client(endpoint) as c:
        response = await c.post("/x")

    assert response.headers["X-Request-Id"] == seen["request_id"]


@pytest.mark.asyncio
async def should_log_rejected_event_for_4xx_status(
    captured_http_logs: ListHandler,
) -> None:
    """Classify a client-error response as a rejected HTTP request."""

    async def endpoint(_: Request) -> Response:
        return JSONResponse({"error": "nope"}, status_code=429)

    async with client(endpoint) as c:
        await c.post("/x")

    record = record_for(captured_http_logs, "http.request.rejected")
    assert record.context["status_code"] == 429


@pytest.mark.asyncio
async def should_log_and_reraise_unhandled_exception(
    captured_http_logs: ListHandler,
) -> None:
    """Log an unhandled error at ERROR level without swallowing the exception."""

    async def endpoint(_: Request) -> Response:
        raise RuntimeError("boom")

    async with client(endpoint) as c:
        with pytest.raises(RuntimeError, match="boom"):
            await c.post("/x")

    record = record_for(captured_http_logs, "http.request.error")
    assert record.levelname == "ERROR"
