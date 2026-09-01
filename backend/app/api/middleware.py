"""ASGI middleware for per-request correlation IDs and access logging.

Implement raw ASGI middleware instead of BaseHTTPMiddleware from starlette
because it disrupts `contextvars` propagation for any subsequent pure ASGI
Middleware. See https://starlette.dev/middleware/#limitations.
"""

import logging
import time
from typing import cast
from uuid import uuid4

from starlette import status
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.handlers import envelope_response
from app.core.logging import log_context
from app.schemas.envelope import ErrorInfo

logger = logging.getLogger(__name__)


class _RequestBodyTooLarge(Exception):
    """Stop downstream request parsing when the raw body crosses its limit."""


class RequestBodyLimitMiddleware:
    """Bound request bodies before FastAPI parses multipart form data."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_bytes: int,
        paths: set[str],
    ) -> None:
        self._app = app
        self._max_body_bytes = max_body_bytes
        self._paths = frozenset(paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject declared or streamed oversized request bodies."""
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in self._paths
        ):
            await self._app(scope, receive, send)
            return

        if self._content_length(scope) > self._max_body_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_body_bytes:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self._app(scope, limited_receive, send)
        except _RequestBodyTooLarge:
            await self._reject(scope, receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int:
        headers = cast(list[tuple[bytes, bytes]], scope.get("headers", []))
        values = [value for name, value in headers if name == b"content-length"]
        if len(values) != 1:
            return 0
        try:
            return int(values[0])
        except ValueError:
            return 0

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        response = envelope_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            ErrorInfo(
                code="REQUEST_BODY_TOO_LARGE",
                message="Request body too large",
                details=None,
            ),
        )
        await response(scope, receive, send)


class RequestLoggingMiddleware:
    """Assign/propagate a request ID and log completion/failure timing.

    Domain-specific rejections (415/429/413 with a precise event name) are
    logged by the router that produced them. This middleware only fills the
    gap: success timing, and 5xx that no handler-level event already covered.
    """

    def __init__(self, app: ASGIApp, exclude_paths: list[str] | None = None) -> None:
        self._app = app
        self._exclude_paths = frozenset(exclude_paths or ())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind the request ID, run the request, and log its outcome."""
        if scope["type"] != "http" or scope.get("path") in self._exclude_paths:
            await self._app(scope, receive, send)
            return

        request_id = self._incoming_request_id(scope) or str(uuid4())
        with log_context(request_id=request_id):
            await self._run_request(scope, receive, send, request_id)

    async def _run_request(
        self, scope: Scope, receive: Receive, send: Send, request_id: str
    ) -> None:
        """Run and log one HTTP request inside an already-bound context."""
        start = time.perf_counter()

        response_state: dict[str, int] = {}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_state["status_code"] = message["status"]
                MutableHeaders(scope=message).append("X-Request-Id", request_id)
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        except Exception:
            if "status_code" in response_state:
                raise

            logger.exception(
                "Unhandled exception during request",
                extra={
                    "event": "http.request.error",
                    "context": {
                        "http_method": scope.get("method"),
                        "http_path": scope.get("path"),
                        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    },
                },
            )
            response_state["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
            response = envelope_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                ErrorInfo(
                    code="INTERNAL_SERVER_ERROR",
                    message="An internal error occurred",
                    details=None,
                ),
            )
            await response(scope, receive, send_wrapper)
            return

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = response_state.get("status_code", 500)
        level = logging.INFO if status_code < 500 else logging.ERROR
        event = (
            "http.request.completed" if status_code < 400 else "http.request.rejected"
        )
        logger.log(
            level,
            "%s %s -> %s",
            scope.get("method"),
            scope.get("path"),
            status_code,
            extra={
                "event": event,
                "context": {
                    "http_method": scope.get("method"),
                    "http_path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            },
        )

    @staticmethod
    def _incoming_request_id(scope: Scope) -> str | None:
        headers = cast(list[tuple[bytes, bytes]], scope.get("headers", []))
        for name, value in headers:
            if name == b"x-request-id":
                return value.decode("latin-1")
        return None
