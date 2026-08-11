"""Tests for limiting upload bodies before downstream parsing."""

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.api.middleware import RequestBodyLimitMiddleware

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def client(
    endpoint: Callable[[Request], Awaitable[Response]],
    *,
    limit: int = 10,
) -> AsyncClient:
    """Build a client whose upload endpoint has a small raw-body limit."""
    app = Starlette(routes=[Route("/invoices", endpoint, methods=["POST"])])
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=limit,
        paths={"/invoices"},
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def should_reject_declared_oversized_body_before_downstream_runs() -> None:
    """Use Content-Length to reject without invoking the parser or dependency."""
    downstream_called = False

    async def endpoint(_: Request) -> Response:
        nonlocal downstream_called
        downstream_called = True
        return JSONResponse({"ok": True})

    async with client(endpoint) as c:
        response = await c.post("/invoices", content=b"x" * 11)

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert downstream_called is False


async def should_limit_streamed_body_without_content_length() -> None:
    """Count chunks when a client omits Content-Length."""

    async def endpoint(request: Request) -> Response:
        await request.body()
        return JSONResponse({"ok": True})

    async def chunks() -> AsyncIterator[bytes]:
        for chunk in (b"123456", b"78901"):
            yield chunk

    async with client(endpoint) as c:
        response = await c.post("/invoices", content=chunks())

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


async def should_leave_other_routes_unrestricted() -> None:
    """Apply the upload ceiling only to configured request paths."""

    async def endpoint(request: Request) -> Response:
        return JSONResponse({"size": len(await request.body())})

    app = Starlette(routes=[Route("/other", endpoint, methods=["POST"])])
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=10,
        paths={"/invoices"},
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        response = await c.post("/other", content=b"x" * 11)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"size": 11}
