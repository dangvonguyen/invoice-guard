"""Database access operations for users."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import UserModel
from app.schemas.user import User, UserCreate


class UserRepository:
    """Repository for performing database operations related to users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: UserCreate) -> bool:
        """Insert a new user and return whether it was newly created."""
        stmt = (
            insert(UserModel)
            .values(**user.model_dump())
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
        return User.model_validate(row)

    async def get_by_id(self, user_id: str) -> User | None:
        """Return the user associated with an ID, if one exists."""
        row = await self._session.get(UserModel, user_id)
        if row is None:
            return row
        return User.model_validate(row)
