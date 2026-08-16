"""Validation and transfer schemas for policy document API data."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.database.models.policy_document import PolicyDocumentStatus


class PolicyDocumentUploadResponse(BaseModel):
    """Response for a successful policy document upload."""

    policy_document_id: UUID
    status: PolicyDocumentStatus
    chunk_count: int


class PolicyDocumentListItem(BaseModel):
    """One document entry in the policy document listing."""

    policy_document_id: UUID
    status: PolicyDocumentStatus
    original_filename: str
    chunk_count: int
    created_at: datetime
