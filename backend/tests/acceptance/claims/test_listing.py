"""Acceptance scenarios for listing an owner's claims."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.claim import ClaimStatus
from app.database.models.user import User
from tests.support.helpers import create_claim

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


async def should_list_the_authenticated_employees_own_claim(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Return a claim the employee submitted."""
    claim = await create_claim(test_db, owner_id=employee.id)
    await test_db.commit()

    response = await client.get("/claims", headers=employee_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["success"] is True
    assert [item["id"] for item in body["data"]] == [str(claim.id)]
    assert body["meta"] == {"total": 1, "offset": 0, "limit": 20}


async def should_exclude_another_employees_claims(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    other_employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Never surface another employee's claim in the caller's list."""
    await create_claim(test_db, owner_id=other_employee.id, attachment_key="other-key")
    own = await create_claim(test_db, owner_id=employee.id, attachment_key="own-key")
    await test_db.commit()

    response = await client.get("/claims", headers=employee_headers)

    body = response.json()
    assert [item["id"] for item in body["data"]] == [str(own.id)]


async def should_reject_unauthenticated_listing(client: AsyncClient) -> None:
    """Require authentication before listing claims."""
    response = await client.get("/claims")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_order_claims_newest_first(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Surface the most recently submitted claim first."""
    now = datetime.now(UTC)
    oldest = await create_claim(
        test_db,
        owner_id=employee.id,
        attachment_key="oldest-key",
        created_at=now - timedelta(hours=2),
    )
    newest = await create_claim(
        test_db,
        owner_id=employee.id,
        attachment_key="newest-key",
        created_at=now,
    )
    await test_db.commit()

    response = await client.get("/claims", headers=employee_headers)

    body = response.json()
    assert [item["id"] for item in body["data"]] == [str(newest.id), str(oldest.id)]


async def should_narrow_the_list_to_claims_needing_the_employees_action(
    client: AsyncClient,
    test_db: AsyncSession,
    employee: User,
    employee_headers: dict[str, str],
) -> None:
    """Filter to claims whose ball is in the employee's court."""
    await create_claim(test_db, owner_id=employee.id, attachment_key="submitted-key")
    returned = await create_claim(
        test_db,
        owner_id=employee.id,
        attachment_key="returned-key",
        status=ClaimStatus.RETURNED_FOR_INFO,
    )
    await test_db.commit()

    response = await client.get(
        "/claims", headers=employee_headers, params={"needs_action": "true"}
    )

    body = response.json()
    assert [item["id"] for item in body["data"]] == [str(returned.id)]
