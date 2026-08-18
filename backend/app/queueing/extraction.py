"""Queue invoice extraction jobs and handle their worker lifecycle."""

import asyncio
import logging
from datetime import date
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
from app.database.models.invoice import InvoiceStatus
from app.database.repositories.invoice import InvoiceRepository
from app.database.repositories.rule_result import RuleResultRepository
from app.database.session import get_session_factory
from app.queueing.jobs.evaluate_rules import evaluate_rules
from app.queueing.jobs.extract_invoice import InvoiceNotFoundError, extract_invoice
from app.services.extraction.grounding import GroundingChecker
from app.services.extraction.model import ExtractedInvoice, OpenAIModelClient
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.text import PdfTextExtractor
from app.services.rules.config import build_rule_config
from app.services.rules.engine import RuleEngine

_EXTRACTION_TIMEOUT_SECONDS = 180
_EXTRACTION_RETRY_INTERVALS_SECONDS = [10, 30]
_FAILURE_CALLBACK_TIMEOUT_SECONDS = 10

# Statuses under which an RQ job is still expected to run to completion
ACTIVE_STATUSES = frozenset(
    {JobStatus.QUEUED, JobStatus.STARTED, JobStatus.DEFERRED, JobStatus.SCHEDULED}
)

logger = logging.getLogger(__name__)


class ExtractionEnqueueError(Exception):
    """Raised when an invoice could not be scheduled for extraction."""


def get_job_id(invoice_id: UUID) -> str:
    """Return the deterministic RQ job id used for one invoice's extraction."""
    return f"extraction-{invoice_id}"


def enqueue(queue: Queue, invoice_id: UUID) -> None:
    """Schedule extraction for a stored invoice, translating broker failures."""
    job_id = get_job_id(invoice_id)
    try:
        if Job.exists(job_id, connection=queue.connection):
            existing = Job.fetch(job_id, connection=queue.connection)
            if existing.get_status(refresh=False) in ACTIVE_STATUSES:
                return

        queue.enqueue(
            execute,
            str(invoice_id),
            job_id=job_id,
            job_timeout=_EXTRACTION_TIMEOUT_SECONDS,
            retry=Retry(
                max=len(_EXTRACTION_RETRY_INTERVALS_SECONDS),
                interval=_EXTRACTION_RETRY_INTERVALS_SECONDS,
            ),
            on_failure=Callback(
                handle_failure,
                timeout=_FAILURE_CALLBACK_TIMEOUT_SECONDS,
            ),
        )
    except RedisError as exc:
        raise ExtractionEnqueueError(f"failed to enqueue invoice {invoice_id}") from exc


async def execute(invoice_id: str) -> None:
    """Entry point: extract fields, evaluate policy rules, then open for review.

    Rule evaluation is a separate step that only runs once extraction has
    successfully produced extracted fields to check. The invoice reaches
    `awaiting_review` only once rule evaluation itself succeeds.
    """
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            invoice_uuid = UUID(invoice_id)
            invoices = InvoiceRepository(session=session)
            invoice = await invoices.get_by_id(invoice_uuid)
            extracted_invoice: ExtractedInvoice | None
            if (
                invoice is not None
                and invoice.status == InvoiceStatus.PROCESSING
                and invoice.extracted_fields is not None
            ):
                # An RQ retry after evaluation failed must resume from the
                # durable extraction result instead of calling the model again.
                extracted_invoice = ExtractedInvoice.model_validate(
                    invoice.extracted_fields
                )
            else:
                extracted_invoice = await extract_invoice(
                    invoice_uuid,
                    invoices=invoices,
                    storage=LocalStorageClient(
                        base_path=Path(settings.STORAGE_LOCAL_PATH)
                    ),
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
            return

    if extracted_invoice is not None:
        try:
            async with session_factory() as session:
                await evaluate_rules(
                    UUID(invoice_id),
                    extracted_invoice=extracted_invoice,
                    rule_results=RuleResultRepository(session=session),
                    rule_engine=RuleEngine(config=build_rule_config(settings)),
                    today=date.today(),
                )
                await InvoiceRepository(session=session).mark_awaiting_review(
                    invoice_id=UUID(invoice_id)
                )
        except Exception:
            logger.exception(
                "Invoice failed to reach review queue after successful extraction",
                extra={
                    "event": "invoice.rule_check.failed",
                    "context": {"invoice_id": invoice_id},
                },
            )
            raise


def handle_failure(
    job: Job,
    connection: Redis,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_traceback: TracebackType | None,
) -> None:
    """Failure callback: open the invoice for review once retries are exhausted."""
    del connection, exc_type, exc_value, exc_traceback

    if job.retries_left != 0:
        return

    invoice_id = UUID(job.args[0])

    async def mark_failed() -> None:
        async with get_session_factory()() as session, session.begin():
            await InvoiceRepository(session=session).mark_awaiting_review(
                invoice_id=invoice_id
            )

    asyncio.run(mark_failed())
