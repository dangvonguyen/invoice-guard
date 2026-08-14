"""Specify the extraction reconcile job's re-enqueue and scheduling behavior."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID

import pytest
import pytest_asyncio
from redis import Redis as SyncRedis
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.queue import EXTRACTION_QUEUE_NAME
from app.database.models.invoice import Invoice, InvoiceStatus
from app.database.models.user import User, UserRole
from app.queueing import reconcile
from app.queueing.extraction import (
    ExtractionEnqueueError,
    extraction_job_id,
    run_extraction_enqueue,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]

STALE_AFTER_SECONDS = get_settings().EXTRACTION_RECONCILE_STALE_AFTER_SECONDS


@pytest_asyncio.fixture
async def owner(test_db: AsyncSession) -> User:
    """Persist the user that owns invoices created in these scenarios."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000020"),
        email="reconcile-owner@example.com",
        hashed_password="unused-hash",
        name="Reconcile Owner",
        role=UserRole.EMPLOYEE,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def reconcile_queue(
    sync_redis: SyncRedis,
    test_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> Queue:
    """Point the reconcile job's queue lookup at the test broker."""
    queue = Queue(EXTRACTION_QUEUE_NAME, connection=sync_redis)
    monkeypatch.setattr(reconcile, "get_extraction_queue", lambda: queue)
    monkeypatch.setattr(reconcile, "get_session_factory", lambda: test_sessionmaker)
    return queue


async def _stuck_pending_invoice(test_db: AsyncSession, *, owner: User) -> Invoice:
    """Persist a pending invoice well past the stale cutoff."""
    invoice = Invoice(
        owner_id=owner.id,
        storage_key="stuck-pending.pdf",
        original_filename="invoice.pdf",
        created_at=datetime.now(UTC) - timedelta(seconds=STALE_AFTER_SECONDS + 60),
    )
    test_db.add(invoice)
    await test_db.flush()
    return invoice


async def should_enqueue_extraction_for_a_stuck_pending_invoice(
    test_db: AsyncSession, owner: User, reconcile_queue: Queue
) -> None:
    """Give a pending invoice with no live job a fresh extraction job."""
    invoice = await _stuck_pending_invoice(test_db, owner=owner)

    await reconcile.reconcile_stuck_pending_invoices()

    job = reconcile_queue.fetch_job(extraction_job_id(invoice.id))
    assert job is not None
    assert job.args == (str(invoice.id),)


async def should_skip_a_pending_invoice_that_already_has_a_live_job(
    test_db: AsyncSession, owner: User, reconcile_queue: Queue
) -> None:
    """Leave a pending invoice alone when its extraction job is still live."""
    invoice = await _stuck_pending_invoice(test_db, owner=owner)
    run_extraction_enqueue(reconcile_queue, invoice.id)

    with patch("app.queueing.reconcile.run_extraction_enqueue") as enqueue:
        await reconcile.reconcile_stuck_pending_invoices()

    enqueue.assert_not_called()


async def should_skip_a_pending_invoice_younger_than_the_stale_cutoff(
    test_db: AsyncSession, owner: User, reconcile_queue: Queue
) -> None:
    """Leave a freshly created pending invoice for its own upload request to enqueue."""
    invoice = Invoice(
        owner_id=owner.id,
        storage_key="fresh-pending.pdf",
        original_filename="invoice.pdf",
        created_at=datetime.now(UTC) - timedelta(seconds=STALE_AFTER_SECONDS - 60),
    )
    test_db.add(invoice)
    await test_db.flush()

    await reconcile.reconcile_stuck_pending_invoices()

    assert reconcile_queue.fetch_job(extraction_job_id(invoice.id)) is None


@pytest.mark.usefixtures("reconcile_queue")
async def should_mark_extraction_failed_when_the_reenqueue_attempt_does_not_succeed(
    test_db: AsyncSession, owner: User
) -> None:
    """Stop retrying an invoice forever once a reconcile enqueue attempt fails."""
    invoice = await _stuck_pending_invoice(test_db, owner=owner)

    with patch(
        "app.queueing.reconcile.run_extraction_enqueue",
        side_effect=ExtractionEnqueueError("broker unavailable"),
    ):
        await reconcile.reconcile_stuck_pending_invoices()

    await test_db.refresh(invoice)
    assert invoice.status == InvoiceStatus.EXTRACTION_FAILED


async def should_reschedule_the_next_tick_after_running(
    reconcile_queue: Queue,
) -> None:
    """Keep the self-rescheduling chain alive after each tick runs."""
    await reconcile.reconcile_stuck_pending_invoices()

    assert reconcile_queue.scheduled_job_registry.count == 1


async def should_collapse_duplicate_seeding_for_the_same_tick_boundary(
    reconcile_queue: Queue,
) -> None:
    """Never schedule two reconcile jobs for the same interval boundary."""
    reconcile.schedule_next_reconcile(reconcile_queue)
    reconcile.schedule_next_reconcile(reconcile_queue)

    assert reconcile_queue.scheduled_job_registry.count == 1
