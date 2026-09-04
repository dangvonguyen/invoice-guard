"""Database access operations for claims."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.claim import Claim


class ClaimRepository:
    """Repository for performing database operations related to claims."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, claim: Claim) -> Claim:
        """Persist a fully-built claim."""
        self._session.add(claim)
        await self._session.commit()
        await self._session.refresh(claim)
        return claim

    async def get_by_id(self, claim_id: UUID) -> Claim | None:
        """Return the claim, if one exists."""
        result = await self._session.execute(select(Claim).where(Claim.id == claim_id))
        return result.scalar_one_or_none()
