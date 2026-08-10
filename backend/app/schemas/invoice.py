"""Validation and transfer schemas for invoice API data."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class InvoiceAccepted(BaseModel):
    """Represent a successful invoice upload."""

    invoice_id: UUID
    status: Literal["pending"]
