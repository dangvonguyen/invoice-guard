"""Dependencies for invoice intake and extraction queueing."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends
from rq import Queue

from app.core.config import get_settings
from app.core.queue import get_extraction_queue
from app.core.rate_limit import RateLimiter, RedisRateLimiter
from app.core.storage import LocalStorageClient, StorageClient
from app.database.repositories.invoice import InvoiceRepository
from app.services.upload.intake import UploadService
from app.services.upload.validation import UploadValidator

from .sessions import RedisDep, SessionManualDep


# Use SessionManualDep so the pending row survives a later storage failure;
# SessionDep would roll back the whole request.
def get_invoice_repository(session: SessionManualDep) -> InvoiceRepository:
    """Create an invoice repository configured with a manually-controlled session."""
    return InvoiceRepository(session=session)


InvoiceRepositoryDep = Annotated[InvoiceRepository, Depends(get_invoice_repository)]


def get_invoice_upload_validator() -> UploadValidator:
    """Create the invoice upload validator from configured limits."""
    settings = get_settings()
    return UploadValidator(max_bytes=settings.UPLOAD_MAX_BYTES)


UploadValidatorDep = Annotated[UploadValidator, Depends(get_invoice_upload_validator)]


def get_upload_rate_limiter(redis: RedisDep) -> RateLimiter:
    """Create the Redis-backed upload rate limiter from configured limits."""
    settings = get_settings()
    return RedisRateLimiter(
        redis=redis,
        limit=settings.UPLOAD_RATE_LIMIT,
        window_seconds=settings.UPLOAD_RATE_LIMIT_WINDOW_SECONDS,
    )


UploadRateLimiterDep = Annotated[RateLimiter, Depends(get_upload_rate_limiter)]


def get_storage_client() -> StorageClient:
    """Create the object storage client - Local disk."""
    settings = get_settings()
    return LocalStorageClient(base_path=Path(settings.STORAGE_LOCAL_PATH))


StorageClientDep = Annotated[StorageClient, Depends(get_storage_client)]


def get_invoice_intake_service(
    validator: UploadValidatorDep,
    rate_limiter: UploadRateLimiterDep,
    invoices: InvoiceRepositoryDep,
    storage: StorageClientDep,
) -> UploadService:
    """Create the invoice intake service from its injected dependencies."""
    return UploadService(
        validator=validator,
        rate_limiter=rate_limiter,
        invoices=invoices,
        storage=storage,
    )


InvoiceIntakeServiceDep = Annotated[UploadService, Depends(get_invoice_intake_service)]


ExtractionQueueDep = Annotated[Queue, Depends(get_extraction_queue)]
