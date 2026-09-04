"""Specify SQL-backed claim persistence behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.claim import (
    Claim,
    ClaimCategory,
    ClaimLineItem,
    ClaimStatus,
    LineItemSource,
)
from app.database.models.user import User
from app.database.repositories.claim import ClaimRepository
from tests.support.helpers import create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns claims created in these scenarios."""
    return await create_user(
        test_db,
        id=UUID("00000000-0000-0000-0000-000000000010"),
        email="claim-owner@example.com",
    )


@pytest.fixture
def repository(test_db: AsyncSession) -> ClaimRepository:
    """Return a claim repository using the test database session."""
    return ClaimRepository(session=test_db)


def build_claim(owner_id: UUID, **overrides: object) -> Claim:
    """A fully-populated transient claim with two line items."""
    fields: dict[str, object] = {
        "owner_id": owner_id,
        "expense_title": "Annual Figma subscription",
        "business_purpose": "Design tooling for the product team.",
        "category": ClaimCategory.SOFTWARE_HOSTING,
        "vendor": "Figma Inc.",
        "invoice_date": datetime(2026, 2, 14, tzinfo=UTC).date(),
        "total_amount": Decimal("144.00"),
        "currency": "USD",
        "original_total_amount": Decimal("144.00"),
        "certified_at": datetime(2026, 3, 1, tzinfo=UTC),
        "attachment_key": "claim-attachment-key",
        "attachment_filename": "figma-invoice.pdf",
        "attachment_content_type": "application/pdf",
        "attachment_bytes": 2048,
    }
    fields.update(overrides)
    return Claim(
        line_items=[
            ClaimLineItem(
                position=1,
                description="Design seat",
                amount=Decimal("120.00"),
                source=LineItemSource.EMPLOYEE,
            ),
            ClaimLineItem(
                position=2,
                description="Dev seat",
                amount=Decimal("24.00"),
                source=LineItemSource.EMPLOYEE,
            ),
        ],
        **fields,
    )


async def should_round_trip_a_claim_with_its_line_items(
    repository: ClaimRepository, owner: User
) -> None:
    """Persist a claim and reload it with its line items in position order."""
    created = await repository.create(build_claim(owner.id))

    loaded = await repository.get_by_id(created.id)

    assert loaded is not None
    assert loaded.status == ClaimStatus.SUBMITTED
    assert loaded.vendor == "Figma Inc."
    assert loaded.original_total_amount == Decimal("144.00")
    assert [(li.position, li.description) for li in loaded.line_items] == [
        (1, "Design seat"),
        (2, "Dev seat"),
    ]


async def should_default_status_to_submitted_when_unset(
    repository: ClaimRepository, owner: User
) -> None:
    """Leave status to the database default of ``submitted``."""
    created = await repository.create(build_claim(owner.id))

    assert created.status == ClaimStatus.SUBMITTED


async def should_cascade_delete_line_items_with_the_claim(
    test_db: AsyncSession, repository: ClaimRepository, owner: User
) -> None:
    """Removing a claim removes its line items through the database cascade."""
    created = await repository.create(build_claim(owner.id))

    await test_db.delete(await test_db.get(Claim, created.id))
    await test_db.commit()

    remaining = await test_db.scalar(
        select(func.count())
        .select_from(ClaimLineItem)
        .where(ClaimLineItem.claim_id == created.id)
    )
    assert remaining == 0
