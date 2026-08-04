"""Test doubles shared across cross backend test suite."""

from app.ports import User


class InMemoryUserRepository:
    """Store test users in memory and look them up by email address."""

    def __init__(self, users: list[User]) -> None:
        self._users = {u.email: u for u in users}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)
