"""Database access operations for users."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User


class UserRepository:
    """Repository for performing database operations related to users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: Mapping[str, Any]) -> bool:
        """Insert a new user and return whether it was newly created."""
        stmt = (
            insert(User)
            .values(user)
            .on_conflict_do_nothing(index_elements=[User.email])
            .returning(User.id)
        )
        return (await self._session.scalar(stmt)) is not None

    async def get_by_email(self, email: str) -> User | None:
        """Return the user associated with an email address, if one exists."""
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user associated with an ID, if one exists."""
        return await self._session.get(User, user_id)
