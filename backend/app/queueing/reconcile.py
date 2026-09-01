"""Recurring tick that re-enqueues extraction for stale processing invoices."""

import logging
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

from redis import Redis, RedisError
from rq import Queue
from rq.job import Job

from app.core.config import get_settings
from app.core.queue import get_extraction_queue
from app.database.repositories.invoice import InvoiceRepository
from app.database.session import get_session_factory
from app.queueing import invoice_processing

# Keeps a failed tick's hash around briefly for debugging
_RECONCILE_TICK_FAILURE_TTL_SECONDS = 3600

logger = logging.getLogger(__name__)


def next_tick(now: datetime, *, interval_seconds: int) -> datetime:
    """Return the next interval boundary strictly after `now`.

    Every caller within the same interval window rounds up to the
    same boundary, so every seeder in the fleet computes the same
    tick id for the same tick.
    """
    boundary_epoch = (
        math.floor(now.timestamp() / interval_seconds) + 1
    ) * interval_seconds
    return datetime.fromtimestamp(boundary_epoch, tz=UTC)


def get_job_id(tick: datetime) -> str:
    """Return the deterministic RQ job id for a reconcile tick."""
    return f"reconcile-processing-invoices-{int(tick.timestamp())}"


def schedule_next(queue: Queue) -> None:
    """Schedule the next reconcile tick, collapsing duplicate seeders.

    Called both at API startup and as the first action of every tick, so
    the self-rescheduling chain survives a failure anywhere else in the
    tick body.
    """
    settings = get_settings()
    tick = next_tick(
        datetime.now(UTC),
        interval_seconds=settings.EXTRACTION_RECONCILE_INTERVAL_SECONDS,
    )
    job_id = get_job_id(tick)

    try:
        if Job.exists(job_id, connection=queue.connection):
            # A currently-executing or already-scheduled tick for this
            # boundary must never be overwritten.
            return

        queue.enqueue_at(
            tick,
            execute,
            job_id=job_id,
            failure_ttl=_RECONCILE_TICK_FAILURE_TTL_SECONDS,
        )
    except RedisError:
        logger.warning(
            "Failed to schedule the next extraction reconcile tick",
            extra={
                "event": "invoice.extraction.reconcile.schedule_failed",
                "context": {"tick": tick.isoformat()},
            },
        )


def has_active_job(invoice_id: UUID, *, connection: Redis) -> bool:
    """Return whether an invoice's extraction job is still expected to run."""
    job_id = invoice_processing.get_job_id(invoice_id)
    if not Job.exists(job_id, connection=connection):
        return False
    job = Job.fetch(job_id, connection=connection)
    return job.get_status(refresh=False) in invoice_processing.ACTIVE_STATUSES


async def execute() -> None:
    """Recurring job: re-enqueue processing invoices with no live extraction job.

    Each eligible invoice gets a single enqueue attempt for this tick; an
    invoice whose attempt does not succeed is marked processing_error
    rather than left processing to be retried indefinitely by future ticks.
    """
    queue = get_extraction_queue()

    schedule_next(queue)

    settings = get_settings()
    stale_cutoff = datetime.now(UTC) - timedelta(
        seconds=settings.EXTRACTION_RECONCILE_STALE_AFTER_SECONDS
    )

    async with get_session_factory()() as session, session.begin():
        invoices = InvoiceRepository(session=session)
        stale_invoices = await invoices.list_old_processing(
            cutoff=stale_cutoff, limit=settings.EXTRACTION_RECONCILE_BATCH_LIMIT
        )

        logger.info(
            "Extraction reconcile tick scanning stale processing invoices",
            extra={
                "event": "invoice.extraction.reconcile.tick_started",
                "context": {"candidate_count": len(stale_invoices)},
            },
        )

        for invoice in stale_invoices:
            if has_active_job(invoice.id, connection=queue.connection):
                continue

            try:
                invoice_processing.enqueue(queue, invoice.id)
            except invoice_processing.ProcessingEnqueueError:
                await invoices.mark_processing_error(invoice_id=invoice.id)
                logger.warning(
                    "Reconciler failed to re-enqueue a stuck invoice; marked failed",
                    extra={
                        "event": "invoice.extraction.reconcile.enqueue_failed",
                        "context": {"invoice_id": str(invoice.id)},
                    },
                )
