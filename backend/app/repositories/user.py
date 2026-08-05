"""Database access operations for users."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel
from app.ports import User


class UserRepository:
    """Repository for performing database operations related to users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> bool:
        """Insert a new user and return whether it was newly created."""
        stmt = (
            insert(UserModel)
            .values(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
            )
            .on_conflict_do_nothing(index_elements=[UserModel.email])
            .returning(UserModel.id)
        )
        return (await self._session.scalar(stmt)) is not None

    async def get_by_email(self, email: str) -> User | None:
        """Return the user associated with an email address, if one exists."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return row
        return User(id=row.id, email=row.email, hashed_password=row.hashed_password)

    async def get_by_id(self, user_id: str) -> User | None:
        """Return the user associated with an ID, if one exists."""
        row = await self._session.get(UserModel, user_id)
        if row is None:
            return row
        return User(id=row.id, email=row.email, hashed_password=row.hashed_password)
