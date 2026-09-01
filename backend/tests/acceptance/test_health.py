"""Acceptance scenarios for service health endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


async def should_report_service_as_live(client: AsyncClient) -> None:
    """Report that the service is available to receive requests."""
    response = await client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
