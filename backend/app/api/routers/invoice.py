"""Routes for invoice document intake."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, InvoiceIntakeServiceDep
from app.schemas.invoice import InvoiceUploadResponse
from app.services.invoice_mime_validator import PayloadTooLargeError

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    current_user: CurrentUser,
    invoice_intake: InvoiceIntakeServiceDep,
    file: Annotated[UploadFile, File()],
) -> InvoiceUploadResponse:
    """Accept an invoice document and enqueue it for processing."""
    content = await file.read()
    try:
        invoice = await invoice_intake.upload(
            owner_id=current_user.id,
            filename=file.filename,
            content_type=file.content_type,
            size=file.size,
            content=content,
        )
    except PayloadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    return InvoiceUploadResponse(invoice_id=invoice.id, status=invoice.status)
