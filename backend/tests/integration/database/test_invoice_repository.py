"""Specify SQL-backed invoice persistence behavior."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User
from app.database.repositories.invoice import InvoiceRepository
from tests.support.helpers import create_invoice, create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns invoices created in these scenarios."""
    return await create_user(
        test_db,
        id=UUID("00000000-0000-0000-0000-000000000010"),
        email="owner@example.com",
    )


@pytest.fixture
def repository(test_db: AsyncSession) -> InvoiceRepository:
    """Return an invoice repository using the test database session."""
    return InvoiceRepository(session=test_db)


async def should_default_status_to_processing(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Create a new invoice row with processing status and the given fields."""
    invoice = await repository.create_processing(
        owner_id=owner.id,
        storage_key="key.pdf",
        original_filename="invoice.pdf",
    )

    assert invoice.status == InvoiceStatus.PROCESSING

    stored = await test_db.scalar(select(Invoice).where(Invoice.id == invoice.id))
    assert stored is not None
    assert stored.owner_id == owner.id
    assert stored.storage_key == "key.pdf"
    assert stored.original_filename == "invoice.pdf"
    assert stored.status == InvoiceStatus.PROCESSING


async def should_generate_a_unique_id_per_invoice(
    repository: InvoiceRepository, owner: User
) -> None:
    """Assign each created invoice a distinct primary key."""
    first = await repository.create_processing(
        owner_id=owner.id, storage_key="a.pdf", original_filename="a.pdf"
    )
    second = await repository.create_processing(
        owner_id=owner.id, storage_key="b.pdf", original_filename="b.pdf"
    )

    assert first.id != second.id


async def should_durably_mark_a_failed_upload(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Transition a processing reservation when its storage write fails."""
    invoice = await repository.create_processing(
        owner_id=owner.id,
        storage_key="failed-key",
        original_filename="invoice.pdf",
    )

    result = await repository.mark_upload_failed(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.UPLOAD_FAILED
    assert result.applied is True
    assert result.status == InvoiceStatus.UPLOAD_FAILED


async def should_not_mark_upload_failed_once_an_invoice_has_left_processing(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Refuse to mark a no-longer-processing invoice as a failed upload."""
    invoice = await create_invoice(
        test_db,
        owner_id=owner.id,
        storage_key="already-reviewed-key",
        status=InvoiceStatus.AWAITING_REVIEW,
    )

    result = await repository.mark_upload_failed(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.AWAITING_REVIEW
    assert result.applied is False
    assert result.status == InvoiceStatus.AWAITING_REVIEW


async def should_durably_mark_a_processing_error(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Transition a processing invoice when its text layer cannot be extracted."""
    invoice = await repository.create_processing(
        owner_id=owner.id,
        storage_key="no-text-layer-key",
        original_filename="invoice.pdf",
    )

    result = await repository.mark_processing_error(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.PROCESSING_ERROR
    assert result.applied is True
    assert result.status == InvoiceStatus.PROCESSING_ERROR


async def should_not_mark_processing_error_once_fields_are_already_extracted(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Keep durable extraction success when a later rule-evaluation retry exhausts."""
    invoice = await repository.create_processing(
        owner_id=owner.id,
        storage_key="already-extracted-key",
        original_filename="invoice.pdf",
    )
    await repository.mark_extracted(
        invoice_id=invoice.id,
        fields={"total_amount": "125.50"},
        confidence="high",
        confidence_reason=None,
    )

    result = await repository.mark_processing_error(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.PROCESSING
    assert invoice.extracted_fields is not None
    assert result.applied is False
    assert result.status == InvoiceStatus.PROCESSING


async def should_persist_extracted_fields_without_changing_status(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Persist extracted fields while leaving the processing status untouched."""
    invoice = await repository.create_processing(
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

    assert invoice.status == InvoiceStatus.PROCESSING
    assert invoice.extracted_fields is not None
    assert invoice.extracted_fields["invoice_number"] == "INV-001"
    assert invoice.extracted_fields["total_amount"] == "125.50"
    assert invoice.extracted_fields["currency"] == "USD"


async def should_mark_a_processing_invoice_awaiting_review(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Open a fully analyzed invoice for review."""
    invoice = await repository.create_processing(
        owner_id=owner.id,
        storage_key="analyzed-key",
        original_filename="invoice.pdf",
    )

    result = await repository.mark_awaiting_review(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.AWAITING_REVIEW
    assert result.applied is True
    assert result.status == InvoiceStatus.AWAITING_REVIEW


async def should_mark_a_processing_error_invoice_awaiting_review(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Open an invoice for review once its retries are exhausted."""
    invoice = await repository.create_processing(
        owner_id=owner.id,
        storage_key="exhausted-retries-key",
        original_filename="invoice.pdf",
    )
    await repository.mark_processing_error(invoice_id=invoice.id)

    await repository.mark_awaiting_review(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == InvoiceStatus.AWAITING_REVIEW


@pytest.mark.parametrize(
    "terminal_status",
    [
        InvoiceStatus.APPROVED,
        InvoiceStatus.REJECTED,
        InvoiceStatus.UPLOAD_FAILED,
    ],
)
async def should_not_resurrect_a_terminal_invoice_into_awaiting_review(
    test_db: AsyncSession,
    repository: InvoiceRepository,
    owner: User,
    terminal_status: InvoiceStatus,
) -> None:
    """Never move a decided or failed-upload invoice into the review queue."""
    invoice = Invoice(
        owner_id=owner.id,
        storage_key=f"terminal-{terminal_status.value}-key",
        original_filename="invoice.pdf",
        status=terminal_status,
    )
    test_db.add(invoice)
    await test_db.flush()

    result = await repository.mark_awaiting_review(invoice_id=invoice.id)
    await test_db.refresh(invoice)

    assert invoice.status == terminal_status
    assert result.applied is False
    assert result.status == terminal_status


async def should_list_only_processing_invoices_older_than_a_cutoff(
    test_db: AsyncSession, repository: InvoiceRepository, owner: User
) -> None:
    """Exclude younger processing rows and non-processing rows of any age."""
    now = datetime.now(UTC)
    old_processing = Invoice(
        owner_id=owner.id,
        storage_key="old-processing.pdf",
        original_filename="old-processing.pdf",
        created_at=now - timedelta(hours=1),
    )
    young_processing = Invoice(
        owner_id=owner.id,
        storage_key="young-processing.pdf",
        original_filename="young-processing.pdf",
        created_at=now - timedelta(seconds=1),
    )
    old_awaiting_review = Invoice(
        owner_id=owner.id,
        storage_key="old-awaiting-review.pdf",
        original_filename="old-awaiting-review.pdf",
        created_at=now - timedelta(hours=1),
        status=InvoiceStatus.AWAITING_REVIEW,
    )
    test_db.add_all([old_processing, young_processing, old_awaiting_review])
    await test_db.flush()

    result = await repository.list_old_processing(
        cutoff=now - timedelta(minutes=30), limit=10
    )

    assert [invoice.id for invoice in result] == [old_processing.id]


async def should_cap_the_processing_batch_at_the_requested_limit(
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

    result = await repository.list_old_processing(cutoff=now, limit=2)

    assert len(result) == 2
