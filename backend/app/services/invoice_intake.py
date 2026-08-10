"""Invoice intake service implementation."""

from uuid import UUID

from app.core.rate_limit import RateLimiter
from app.core.storage import StorageClient
from app.database.models import Invoice
from app.services.interfaces import InvoiceRepository
from app.services.invoice_mime_validator import InvoiceMimeValidator


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
            filename=filename, content_type=content_type, size=size
        )
        await self._rate_limiter.allow(key=owner_id, scope=self._rate_limit_key_prefix)
        storage_key = self._storage.generate_key()
        invoice = await self._invoices.create_pending(
            owner_id=owner_id, storage_key=storage_key, original_filename=filename
        )
        await self._storage.save(key=storage_key, content=content)
        return invoice
