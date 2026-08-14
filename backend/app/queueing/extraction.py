"""Queue invoice extraction jobs and handle their worker lifecycle."""

import asyncio
import logging
from pathlib import Path
from types import TracebackType
from uuid import UUID

from openai import AsyncOpenAI
from redis import Redis
from redis.exceptions import RedisError
from rq import Callback, Queue, Retry
from rq.job import Job, JobStatus

from app.core.config import get_settings, unwrap_secret
from app.core.storage import LocalStorageClient
from app.database.repositories.invoice import InvoiceRepository
from app.database.session import get_session_factory
from app.jobs.extract_invoice import InvoiceNotFoundError, extract_invoice
from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.model import OpenAIModelClient
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.text_extractor import PdfTextExtractor

_EXTRACTION_TIMEOUT_SECONDS = 180
_EXTRACTION_RETRY_INTERVALS_SECONDS = [10, 30]
_FAILURE_CALLBACK_TIMEOUT_SECONDS = 10

# Statuses under which an RQ job is still expected to run to completion
LIVE_JOB_STATUSES = frozenset(
    {JobStatus.QUEUED, JobStatus.STARTED, JobStatus.DEFERRED, JobStatus.SCHEDULED}
)

logger = logging.getLogger(__name__)


class ExtractionEnqueueError(Exception):
    """Raised when an invoice could not be scheduled for extraction."""


def extraction_job_id(invoice_id: UUID) -> str:
    """Return the deterministic RQ job id used for one invoice's extraction."""
    return f"extraction-{invoice_id}"


def run_extraction_enqueue(queue: Queue, invoice_id: UUID) -> None:
    """Schedule extraction for a stored invoice, translating broker failures."""
    job_id = extraction_job_id(invoice_id)
    try:
        if Job.exists(job_id, connection=queue.connection):
            existing = Job.fetch(job_id, connection=queue.connection)
            if existing.get_status(refresh=False) in LIVE_JOB_STATUSES:
                return

        queue.enqueue(
            run_extraction_job,
            str(invoice_id),
            job_id=job_id,
            job_timeout=_EXTRACTION_TIMEOUT_SECONDS,
            retry=Retry(
                max=len(_EXTRACTION_RETRY_INTERVALS_SECONDS),
                interval=_EXTRACTION_RETRY_INTERVALS_SECONDS,
            ),
            on_failure=Callback(
                on_extraction_failure,
                timeout=_FAILURE_CALLBACK_TIMEOUT_SECONDS,
            ),
        )
    except RedisError as exc:
        raise ExtractionEnqueueError(f"failed to enqueue invoice {invoice_id}") from exc


async def run_extraction_job(invoice_id: str) -> None:
    """Entry point: extract fields for one stored invoice."""
    settings = get_settings()
    async with get_session_factory()() as session, session.begin():
        try:
            await extract_invoice(
                UUID(invoice_id),
                invoices=InvoiceRepository(session=session),
                storage=LocalStorageClient(base_path=Path(settings.STORAGE_LOCAL_PATH)),
                text_extractor=PdfTextExtractor(),
                extraction_pipeline=ExtractionPipeline(
                    model=OpenAIModelClient(
                        client=AsyncOpenAI(
                            api_key=unwrap_secret(settings.OPENAI_API_KEY)
                        ),
                        model=settings.OPENAI_EXTRACTION_MODEL,
                    ),
                    grounding_checker=GroundingChecker(),
                ),
            )
        except InvoiceNotFoundError:
            logger.warning(
                "Invoice extraction skipped because the invoice no longer exists",
                extra={
                    "event": "invoice.extraction.invoice_not_found",
                    "context": {"invoice_id": invoice_id},
                },
            )


def on_extraction_failure(
    job: Job,
    connection: Redis,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_traceback: TracebackType | None,
) -> None:
    """Failure callback: mark the invoice failed once retries are exhausted."""
    del connection, exc_type, exc_value, exc_traceback

    if job.retries_left != 0:
        return

    invoice_id = UUID(job.args[0])

    async def run() -> None:
        async with get_session_factory()() as session, session.begin():
            await InvoiceRepository(session=session).mark_extraction_failed(
                invoice_id=invoice_id
            )

    asyncio.run(run())
