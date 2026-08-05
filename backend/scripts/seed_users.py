"""Seed users from a JSON file into the application database."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from app.adapters.password_hasher import PasswordHasher
from app.database.db import get_session_factory
from app.ports import User
from app.repositories.user import UserRepository


class SeedUser(BaseModel):
    """Plaintext user information accepted by the seeding script."""

    email: str
    password: str


def load_users(path: Path) -> list[SeedUser]:
    """Load user records from a JSON file."""
    data: object = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("users file must contain a JSON list")

    users: list[SeedUser] = []
    for index, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValueError(f"user at index {index} must be a JSON object")

        users.append(SeedUser(**record))

    return users


async def seed_users(
    path: Path, repository: UserRepository, password_hasher: PasswordHasher
) -> int:
    """Seed every user in a file and return the number newly inserted."""
    inserted_count = 0
    for seed_user in load_users(path):
        user = User(
            id=str(uuid4()),
            email=seed_user.email,
            hashed_password=password_hasher.hash(seed_user.password),
        )
        inserted_count += await repository.create(user)
    return inserted_count


async def run(path: Path) -> int:
    """Seed users using the application's database-backed collaborators."""
    session_factory = get_session_factory()
    async with session_factory() as session, session.begin():
        return await seed_users(
            path,
            UserRepository(session=session),
            PasswordHasher(),
        )


def main() -> None:
    """Run the user seeder from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to a JSON users file")
    args = parser.parse_args()
    inserted_count = asyncio.run(run(args.path))
    print(f"Inserted {inserted_count} user(s).")


if __name__ == "__main__":
    main()
