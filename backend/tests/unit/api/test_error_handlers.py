"""Tests for the shared exception handlers and their envelope shape."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from starlette import status

from app.api.handlers import register_exception_handlers
from app.core.errors import ForbiddenError, NotFoundError

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]


class Payload(BaseModel):
    amount: int


@pytest.fixture
def test_app() -> FastAPI:
    """Create a FastAPI application with all shared exception handlers registered."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("User not found")

    @app.get("/forbidden")
    async def raise_forbidden() -> None:
        raise ForbiddenError("Not your resource")

    @app.get("/unhandled")
    async def raise_unhandled() -> None:
        raise RuntimeError("db connection reset")

    @app.post("/validate")
    async def validate_body(payload: Payload) -> dict[str, Any]:
        return {"amount": payload.amount}

    @app.get("/raw-http")
    async def raise_raw_http() -> None:
        raise HTTPException(status_code=403, detail="Access denied")

    return app


@pytest_asyncio.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create an async client configured to exercise the test application."""
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_domain_not_found_returns_envelope_shape(client: AsyncClient) -> None:
    """Verify that a domain not-found error uses the standard envelope."""
    resp = await client.get("/not-found")

    assert resp.status_code == status.HTTP_404_NOT_FOUND
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "User not found"
    assert body["error"]["details"] is None


async def test_domain_forbidden_returns_envelope_shape(client: AsyncClient) -> None:
    """Verify that a domain forbidden error uses the standard envelope."""
    resp = await client.get("/forbidden")

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "FORBIDDEN"


async def test_pydantic_body_validation_returns_envelope_with_field_details(
    client: AsyncClient,
) -> None:
    """Verify that body validation errors include structured field details."""
    resp = await client.post("/validate", json={"amount": "not-a-number"})

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "amount"


async def test_raw_http_exception_is_normalized(client: AsyncClient) -> None:
    """Verify that a raw HTTP exception is converted to the standard envelope."""
    resp = await client.get("/raw-http")

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["message"] == "Access denied"


async def test_unhandled_exception_returns_generic_message(client: AsyncClient) -> None:
    """Verify that unhandled exceptions return a safe generic error message."""
    resp = await client.get("/unhandled")

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["message"] == "An internal error occurred"
    assert "db connection reset" not in body["error"]["message"]
