"""Specify SQL-backed invoice persistence behavior."""

from datetime import UTC, datetime, timedelta
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


async def should_durably_mark_a_failed_upload(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Transition a pending reservation when its storage write fails."""
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key="failed-key",
        original_filename="invoice.pdf",
    )

    await repository.mark_upload_failed(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.UPLOAD_FAILED


async def should_durably_mark_a_failed_extraction(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Transition a pending invoice when its text layer cannot be extracted."""
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key="no-text-layer-key",
        original_filename="invoice.pdf",
    )

    await repository.mark_extraction_failed(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.EXTRACTION_FAILED


async def should_durably_mark_an_invoice_as_extracted(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Persist extracted fields and transition the invoice to extracted."""
    invoice = await repository.create_pending(
        owner_id=owner.id,
        storage_key="extracted-key",
        original_filename="invoice.pdf",
    )
    extracted_result = {
        "invoice_number": "INV-001",
        "total_amount": "125.50",
        "currency": "USD",
    }

    await repository.mark_extracted(
        invoice_id=invoice.id,
        fields=extracted_result,
        confidence="high",
        confidence_reason=None,
    )
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.EXTRACTED
    assert invoice.extracted_fields is not None
    assert invoice.extracted_fields["invoice_number"] == "INV-001"
    assert invoice.extracted_fields["total_amount"] == "125.50"
    assert invoice.extracted_fields["currency"] == "USD"


async def should_list_only_pending_invoices_older_than_a_cutoff(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Exclude younger pending rows and non-pending rows of any age."""
    now = datetime.now(UTC)
    old_pending = Invoice(
        owner_id=owner.id,
        storage_key="old-pending.pdf",
        original_filename="old-pending.pdf",
        created_at=now - timedelta(hours=1),
    )
    young_pending = Invoice(
        owner_id=owner.id,
        storage_key="young-pending.pdf",
        original_filename="young-pending.pdf",
        created_at=now - timedelta(seconds=1),
    )
    old_extracted = Invoice(
        owner_id=owner.id,
        storage_key="old-extracted.pdf",
        original_filename="old-extracted.pdf",
        created_at=now - timedelta(hours=1),
        status=InvoiceStatus.EXTRACTED,
    )
    test_db.add_all([old_pending, young_pending, old_extracted])
    await test_db.flush()

    result = await repository.list_old_pending(
        cutoff=now - timedelta(minutes=30), limit=10
    )

    assert [invoice.id for invoice in result] == [old_pending.id]


async def should_cap_the_pending_batch_at_the_requested_limit(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Bound a single scan's results to the requested batch limit."""
    now = datetime.now(UTC)
    stale_invoices = [
        Invoice(
            owner_id=owner.id,
            storage_key=f"stale-{index}.pdf",
            original_filename=f"stale-{index}.pdf",
            created_at=now - timedelta(hours=1),
        )
        for index in range(3)
    ]
    test_db.add_all(stale_invoices)
    await test_db.flush()

    result = await repository.list_old_pending(cutoff=now, limit=2)

    assert len(result) == 2
