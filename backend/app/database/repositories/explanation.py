"""Database access operations for persisted review-flag explanations."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.explanation import Explanation


class ExplanationRepository:
    """Repository for performing database operations related to explanations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_rule_result(self, rule_result_id: UUID) -> Explanation | None:
        """Return the persisted explanation for a rule-result row, if any."""
        result = await self._session.execute(
            select(Explanation).where(Explanation.rule_result_id == rule_result_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        rule_result_id: UUID,
        narrative: str,
        citations: list[dict[str, Any]],
        generated_by_model: str,
    ) -> Explanation:
        """Persist a newly generated explanation for a rule-result row."""
        explanation = Explanation(
            rule_result_id=rule_result_id,
            narrative=narrative,
            citations=citations,
            generated_by_model=generated_by_model,
        )
        self._session.add(explanation)
        await self._session.flush()
        return explanation
