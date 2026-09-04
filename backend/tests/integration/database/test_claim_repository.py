"""Specify SQL-backed claim persistence behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.claim import Claim, ClaimCategory, ClaimStatus
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
    """A fully-populated transient claim."""
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
    return Claim(**fields)


async def should_round_trip_a_claim(repository: ClaimRepository, owner: User) -> None:
    """Persist a claim and reload it."""
    created = await repository.create(build_claim(owner.id))

    loaded = await repository.get_by_id(created.id)

    assert loaded is not None
    assert loaded.status == ClaimStatus.SUBMITTED
    assert loaded.vendor == "Figma Inc."
    assert loaded.original_total_amount == Decimal("144.00")


async def should_default_status_to_submitted_when_unset(
    repository: ClaimRepository, owner: User
) -> None:
    """Leave status to the database default of ``submitted``."""
    created = await repository.create(build_claim(owner.id))

    assert created.status == ClaimStatus.SUBMITTED
