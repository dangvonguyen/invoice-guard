"""Dependencies for recording a reviewer's final invoice decision."""

from typing import Annotated

from fastapi import Depends

from app.database.repositories.decision import DecisionRepository
from app.services.review.decision import DecisionService

from .sessions import SessionManualDep


# Use the manually-controlled session dependency so a decision's insert and
# an invoice's status update land in one shared transaction.
def get_decision_repository(session: SessionManualDep) -> DecisionRepository:
    """Create a decision repository configured with a manually-controlled session."""
    return DecisionRepository(session=session)


DecisionRepositoryDep = Annotated[DecisionRepository, Depends(get_decision_repository)]


def get_decision_service(decisions: DecisionRepositoryDep) -> DecisionService:
    """Create the decision service from its injected dependencies."""
    return DecisionService(decisions=decisions)


DecisionServiceDep = Annotated[DecisionService, Depends(get_decision_service)]
