"""Dependencies for claims."""

from typing import Annotated

from fastapi import Depends


def get_claim_submission_service() -> None:
    raise NotImplementedError()


ClaimSubmissionServiceDep = Annotated[None, Depends(get_claim_submission_service)]
