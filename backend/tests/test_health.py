"""Tests for service health-check endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_live_health() -> None:
    """Report a healthy status while the application is running."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        response = await ac.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
