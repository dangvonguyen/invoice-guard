"""Invoice intake service implementation."""

from uuid import UUID

from app.schemas.invoice import InvoiceAccepted
from app.services.interfaces import (
    InvoiceRepository,
    InvoiceValidator,
    RateLimiter,
    StorageClient,
)


class InvoiceIntakeService:
    """Coordinate validation, reservation, and storage of invoice uploads."""

    def __init__(
        self,
        validator: InvoiceValidator,
        rate_limiter: RateLimiter,
        invoices: InvoiceRepository,
        storage: StorageClient,
    ) -> None:
        self._validator = validator
        self._rate_limiter = rate_limiter
        self._invoices = invoices
        self._storage = storage

    async def upload(
        self, owner_id: UUID, filename: str, content_type: str, content: bytes
    ) -> InvoiceAccepted:
        """Accept an invoice upload, return the persisted pending state."""
        self._validator.validate(
            filename=filename, content_type=content_type, size=len(content)
        )
        await self._rate_limiter.allow(owner_id)
        storage_key = self._storage.generate_key()
        invoice_id = await self._invoices.create(
            owner_id=owner_id, storage_key=storage_key, original_filename=filename
        )
        await self._storage.save(key=storage_key, content=content)
        return InvoiceAccepted(invoice_id=invoice_id, status="pending")
