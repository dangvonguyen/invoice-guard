"""Database access operations for claims."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.claim import Claim, ClaimStatus

_NEEDS_EMPLOYEE_ACTION_STATUSES = (ClaimStatus.RETURNED_FOR_INFO,)


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

    async def get_for_owner(self, claim_id: UUID, owner_id: UUID) -> Claim | None:
        """Return the claim if it exists and belongs to `owner_id`."""
        result = await self._session.execute(
            select(Claim).where(Claim.id == claim_id, Claim.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list_for_owner(
        self,
        owner_id: UUID,
        offset: int,
        limit: int,
        *,
        needs_action: bool = False,
    ) -> tuple[Sequence[Claim], int]:
        """Return a page of an owner's claims and the total count, newest first."""
        conditions = [Claim.owner_id == owner_id]
        if needs_action:
            conditions.append(Claim.status.in_(_NEEDS_EMPLOYEE_ACTION_STATUSES))

        total = await self._session.scalar(
            select(func.count()).select_from(Claim).where(*conditions)
        )

        result = await self._session.execute(
            select(Claim)
            .where(*conditions)
            .order_by(Claim.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all(), total or 0
