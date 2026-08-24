"""Reviewer-facing schema for a generated review-flag explanation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CitationView(BaseModel):
    """One policy chunk cited by a generated explanation."""

    chunk_id: UUID
    section_label: str | None
    content: str


class ExplanationView(BaseModel):
    """A generated, policy-grounded explanation for one review flag."""

    explanation: str
    citations: list[CitationView]
    generated_by_model: str
    generated_at: datetime
