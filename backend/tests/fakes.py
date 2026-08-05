"""Test doubles shared across cross backend test suite."""

from app.schemas.user import User


class InMemoryUserRepository:
    """Store test users in memory and look them up by email and ID."""

    def __init__(self, users: list[User]) -> None:
        self._users = users

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users if user.email == email), None)

    async def get_by_id(self, user_id: str) -> User | None:
        return next((user for user in self._users if user.id == user_id), None)
