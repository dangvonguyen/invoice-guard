"""Database model for a persisted, generated review-flag explanation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Explanation(Base):
    """Cache the one generated explanation for a rule-result's review flag."""

    __tablename__ = "explanations"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    rule_result_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("invoice_rule_results.id", ondelete="CASCADE"),
        unique=True,
    )
    narrative: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
