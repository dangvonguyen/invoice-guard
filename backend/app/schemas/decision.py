"""Validation and transfer schemas for a reviewer's final invoice decision."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.database.models.decision import InvoiceDecisionOutcome


class DecisionRequest(BaseModel):
    """Request body for recording a decision."""

    outcome: InvoiceDecisionOutcome
    reason: str = Field(min_length=1)


class DecisionView(BaseModel):
    """The final decision as shown to both the employee and the reviewer."""

    outcome: InvoiceDecisionOutcome
    reason: str
    decided_by: str
    decided_at: datetime
