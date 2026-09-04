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


async def should_only_return_a_claim_to_its_owner(
    repository: ClaimRepository, owner: User, test_db: AsyncSession
) -> None:
    """Refuse to resolve a claim for a non-owning caller."""
    other = await create_user(test_db, email="not-the-owner@example.com")
    created = await repository.create(build_claim(owner.id))

    assert await repository.get_for_owner(created.id, owner.id) is not None
    assert await repository.get_for_owner(created.id, other.id) is None


async def should_list_only_the_owners_claims_newest_first(
    repository: ClaimRepository, owner: User, test_db: AsyncSession
) -> None:
    """Scope the list to the owner and order it newest first."""
    other = await create_user(test_db, email="someone-else@example.com")
    await repository.create(build_claim(other.id, attachment_key="other-key"))
    older = await repository.create(
        build_claim(
            owner.id,
            attachment_key="older-key",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    newer = await repository.create(
        build_claim(
            owner.id,
            attachment_key="newer-key",
            created_at=datetime(2026, 2, 1, tzinfo=UTC),
        )
    )

    claims, total = await repository.list_for_owner(owner.id, offset=0, limit=10)

    assert total == 2
    assert [claim.id for claim in claims] == [newer.id, older.id]


async def should_narrow_the_list_to_claims_needing_employee_action(
    repository: ClaimRepository, owner: User
) -> None:
    """Only surface claims returned for info under the needs-action filter."""
    await repository.create(build_claim(owner.id, attachment_key="submitted-key"))
    returned = await repository.create(
        build_claim(
            owner.id,
            attachment_key="returned-key",
            status=ClaimStatus.RETURNED_FOR_INFO,
        )
    )

    claims, total = await repository.list_for_owner(
        owner.id, offset=0, limit=10, needs_action=True
    )

    assert total == 1
    assert [claim.id for claim in claims] == [returned.id]
