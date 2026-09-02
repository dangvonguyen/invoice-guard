"""Routes for claim submission."""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import ClaimSubmissionServiceDep, CurrentUser
from app.core.config import get_settings
from app.schemas.claim import ClaimSubmissionRequest, ClaimSubmissionResponse
from app.schemas.envelope import ResponseEnvelope

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_claim(
    current_user: CurrentUser,
    submission: ClaimSubmissionServiceDep,
    data: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> ResponseEnvelope[ClaimSubmissionResponse, None]:
    """Submit a claim with associated document."""
    content = await file.read(get_settings().UPLOAD_MAX_BYTES + 1)
    request = ClaimSubmissionRequest.model_validate_json(data)
    claim = await submission.submit(
        owner_id=current_user.id,
        request=request,
        filename=file.filename,
        content_type=file.content_type,
        content_length=len(content),
        content=content,
    )
    return ResponseEnvelope(data=ClaimSubmissionResponse.model_validate(claim))
