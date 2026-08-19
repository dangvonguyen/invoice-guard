"""Validation and transfer schemas for policy document API data."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.database.models.policy_document import PolicyDocumentStatus


class PolicyDocumentResponseBase(BaseModel):
    """Common fields shared by every policy document response shape."""

    model_config = {
        "from_attributes": True,
    }

    id: UUID
    status: PolicyDocumentStatus


class PolicyDocumentUploadResponse(PolicyDocumentResponseBase):
    """Response for a successful policy document upload."""

    chunk_count: int


class PolicyDocumentListItem(PolicyDocumentResponseBase):
    """One document entry in the policy document listing."""

    original_filename: str
    chunk_count: int
    created_at: datetime
