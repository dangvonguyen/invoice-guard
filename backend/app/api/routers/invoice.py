"""Routes for invoice document intake."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentUser, InvoiceIntakeServiceDep
from app.schemas.invoice import InvoiceUploadResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    current_user: CurrentUser,
    invoice_intake: InvoiceIntakeServiceDep,
    file: Annotated[UploadFile, File()],
) -> InvoiceUploadResponse:
    """Accept an invoice document and enqueue it for processing."""
    content = await file.read()
    invoice = await invoice_intake.upload(
        owner_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    return InvoiceUploadResponse(invoice_id=invoice.id, status=invoice.status)
