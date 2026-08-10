"""Specify SQL-backed invoice persistence behavior."""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User, UserRole
from app.database.repositories.invoice import InvoiceRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns invoices created in these scenarios."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000010"),
        email="owner@example.com",
        hashed_password="unused-hash",
        name="Owner",
        role=UserRole.EMPLOYEE,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def repository(test_db: AsyncSession) -> InvoiceRepository:
    """Return an invoice repository using the test database session."""
    return InvoiceRepository(session=test_db)


async def should_default_status_to_pending(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Create a new invoice row with pending status and the given fields."""
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key="key.pdf",
        original_filename="invoice.pdf",
    )

    assert invoice.status == InvoiceStatus.PENDING

    stored = await test_db.scalar(select(Invoice).where(Invoice.id == invoice.id))
    assert stored is not None
    assert stored.owner_id == owner.id
    assert stored.storage_key == "key.pdf"
    assert stored.original_filename == "invoice.pdf"
    assert stored.status == InvoiceStatus.PENDING


async def should_generate_a_unique_id_per_invoice(
    repository: InvoiceRepository, owner: User
) -> None:
    """Assign each created invoice a distinct primary key."""
    first = await repository.create_pending(
        owner_id=owner.id, storage_key="a.pdf", original_filename="a.pdf"
    )
    second = await repository.create_pending(
        owner_id=owner.id, storage_key="b.pdf", original_filename="b.pdf"
    )

    assert first.id != second.id
