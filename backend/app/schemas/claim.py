"""Validation and transfer schemas for claim submission."""

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.database.models.claim import ClaimCategory, ClaimStatus

TrimmedTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
TrimmedPurpose = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
PositiveAmount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
NonNegativeAmount = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class ClaimCreateRequest(BaseModel):
    """Request data for creating a claim."""

    expense_title: TrimmedTitle
    business_purpose: TrimmedPurpose
    category: ClaimCategory
    cost_center: str | None = None
    vendor: NonEmptyString
    invoice_number: str | None = None
    invoice_date: date
    total_amount: PositiveAmount
    currency: Annotated[str, StringConstraints(min_length=3, max_length=3)]
    certified: bool

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        upper = value.upper()
        if not upper.isalpha():
            raise ValueError("currency must be a 3-letter alphabetic ISO code")
        return upper

    @model_validator(mode="after")
    def _require_certification(self) -> "ClaimCreateRequest":
        if self.certified is not True:
            raise ValueError("submission must be certified")
        return self


class ClaimCreateResponse(BaseModel):
    """Response after successfully creating a claim."""

    model_config = {"from_attributes": True}

    id: UUID
    status: ClaimStatus
