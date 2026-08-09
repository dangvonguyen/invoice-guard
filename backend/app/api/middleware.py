"""ASGI middleware for per-request correlation IDs and access logging.

Implement raw ASGI middleware instead of BaseHTTPMiddleware from starlette
because it disrupts `contextvars` propagation for any subsequent pure ASGI
Middleware. See https://starlette.dev/middleware/#limitations.
"""

import logging
import time
from typing import cast
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import bind_request_id, bind_user_id

logger = logging.getLogger(__name__)


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
        bind_request_id(request_id)
        bind_user_id(None)

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
            if "status_code" in response_state:
                bind_request_id(None)
                bind_user_id(None)
                raise

            response_state["status_code"] = 500
            response = PlainTextResponse("Internal Server Error", status_code=500)
            try:
                await response(scope, receive, send_wrapper)
            finally:
                bind_request_id(None)
                bind_user_id(None)
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
        bind_request_id(None)
        bind_user_id(None)

    @staticmethod
    def _incoming_request_id(scope: Scope) -> str | None:
        headers = cast(list[tuple[bytes, bytes]], scope.get("headers", []))
        for name, value in headers:
            if name == b"x-request-id":
                return value.decode("latin-1")
        return None
