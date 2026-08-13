"""RQ entry points: synchronous job functions wiring real collaborators."""

import asyncio
from pathlib import Path
from uuid import UUID

from openai import AsyncOpenAI

from app.core.config import get_settings, unwrap_secret
from app.core.storage import LocalStorageClient
from app.database.repositories.invoice import InvoiceRepository
from app.database.session import get_session_factory
from app.jobs.extract_invoice import extract_invoice
from app.services.extraction_model import OpenAIExtractionModelClient
from app.services.extraction_service import ExtractionService
from app.services.span_grounding import SpanGroundingChecker
from app.services.text_extractor import PdfTextExtractor


def run_extraction_job(invoice_id: str) -> None:
    """Synchronous RQ entry point: extract fields for one stored invoice."""
    asyncio.run(_run_extraction_job(UUID(invoice_id)))


async def _run_extraction_job(invoice_id: UUID) -> None:
    settings = get_settings()
    async with get_session_factory()() as session, session.begin():
        await extract_invoice(
            invoice_id,
            invoices=InvoiceRepository(session=session),
            storage=LocalStorageClient(base_path=Path(settings.STORAGE_LOCAL_PATH)),
            text_extractor=PdfTextExtractor(),
            extraction_service=ExtractionService(
                model=OpenAIExtractionModelClient(
                    client=AsyncOpenAI(api_key=unwrap_secret(settings.OPENAI_API_KEY)),
                    model=settings.OPENAI_EXTRACTION_MODEL,
                ),
                grounding_checker=SpanGroundingChecker(),
            ),
        )
