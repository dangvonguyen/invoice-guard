"""Build read-facing views of a claim."""

from app.database.models.claim import Claim
from app.schemas.claim import ClaimAttachmentResponse, ClaimResponse


def to_claim_response(claim: Claim) -> ClaimResponse:
    """Assemble the owner-facing detail view of one claim."""
    return ClaimResponse(
        id=claim.id,
        status=claim.status,
        expense_title=claim.expense_title,
        business_purpose=claim.business_purpose,
        category=claim.category,
        cost_center=claim.cost_center,
        vendor=claim.vendor,
        invoice_number=claim.invoice_number,
        invoice_date=claim.invoice_date,
        total_amount=claim.total_amount,
        currency=claim.currency,
        created_at=claim.created_at,
        attachment=ClaimAttachmentResponse(
            filename=claim.attachment_filename,
            content_type=claim.attachment_content_type,
            url=f"/claims/{claim.id}/attachment",
        ),
    )
