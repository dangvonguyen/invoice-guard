"""Invoice intake service implementation."""

from uuid import UUID

from app.core.logging import bind_invoice_id
from app.core.rate_limit import RateLimiter
from app.core.storage import StorageClient, StorageWriteError
from app.database.models import Invoice
from app.services.interfaces import InvoiceRepository
from app.services.invoice_mime_validator import InvoiceMimeValidator


class UploadRateLimitExceededError(Exception):
    """Raised when a caller has exceeded their upload rate limit."""


class InvoiceStorageUnavailableError(Exception):
    """Raised when a validated upload cannot be persisted to storage."""


class InvoiceIntakeService:
    """Coordinate validation, reservation, and storage of invoice uploads."""

    def __init__(
        self,
        validator: InvoiceMimeValidator,
        rate_limiter: RateLimiter,
        invoices: InvoiceRepository,
        storage: StorageClient,
        rate_limit_key_prefix: str = "invoice-upload",
    ) -> None:
        self._validator = validator
        self._rate_limiter = rate_limiter
        self._invoices = invoices
        self._storage = storage
        self._rate_limit_key_prefix = rate_limit_key_prefix

    async def upload(
        self,
        owner_id: UUID,
        filename: str | None,
        content_type: str | None,
        size: int | None,
        content: bytes,
    ) -> Invoice:
        """Accept an invoice upload, return the persisted pending state."""
        self._validator.validate(
            filename=filename,
            content_type=content_type,
            size=size,
            content=content,
        )

        if not await self._rate_limiter.allow(
            key=owner_id, scope=self._rate_limit_key_prefix
        ):
            raise UploadRateLimitExceededError(
                f"upload rate limit exceeded for {owner_id}"
            )

        storage_key = self._storage.generate_key()
        invoice = await self._invoices.create_pending(
            owner_id=owner_id, storage_key=storage_key, original_filename=filename or ""
        )

        # Bind the ID so structured logs can be correlated with this invoice.
        # Lightweight test doubles may return None here.
        if invoice is not None:
            bind_invoice_id(str(invoice.id))

        try:
            await self._storage.save(key=storage_key, content=content)
        except StorageWriteError as exc:
            await self._invoices.mark_upload_failed(invoice_id=invoice.id)
            raise InvoiceStorageUnavailableError(
                f"storage failed for invoice {invoice.id}"
            ) from exc
        return invoice
