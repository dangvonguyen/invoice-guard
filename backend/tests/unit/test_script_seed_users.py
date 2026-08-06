"""Specify how users are loaded and seeded by the provisioning script."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, call

import pytest

from app.schemas.user import UserCreate
from scripts.seed_users import SeedUser, load_users, seed_users

pytestmark = pytest.mark.unit


@pytest.fixture
def users_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file containing user records."""
    file = tmp_path / "users.json"
    file.write_text(
        json.dumps(
            [
                {"email": "first@example.com", "password": "password-1"},
                {"email": "second@example.com", "password": "password-2"},
            ]
        )
    )
    return file


def should_load_users_from_json_file(users_file: Path) -> None:
    """Load email and plaintext password from every JSON record."""
    assert load_users(users_file) == [
        SeedUser(email="first@example.com", password="password-1"),
        SeedUser(email="second@example.com", password="password-2"),
    ]


@pytest.mark.asyncio
async def should_hash_and_insert_each_loaded_user(users_file: Path) -> None:
    """Attempt every record and return the number of newly inserted users."""
    repository = AsyncMock()
    repository.create.side_effect = [True, True]
    password_hasher = Mock()
    password_hasher.hash.side_effect = ["hash-1", "hash-2"]

    inserted_count = await seed_users(users_file, repository, password_hasher)

    assert password_hasher.hash.call_args_list == [
        call("password-1"),
        call("password-2"),
    ]
    inserted_users = [args.args[0] for args in repository.create.await_args_list]
    assert [(user.email, user.hashed_password) for user in inserted_users] == [
        ("first@example.com", "hash-1"),
        ("second@example.com", "hash-2"),
    ]
    assert all(isinstance(user, UserCreate) and user.id for user in inserted_users)
    assert inserted_count == 2


@pytest.mark.asyncio
async def should_exclude_existing_user_from_inserted_count(tmp_path: Path) -> None:
    """Count a user already present in the database as a no-op."""
    users_file = tmp_path / "users.json"
    users_file.write_text(
        json.dumps(
            [
                {"email": "user@example.com", "password": "password-1"},
            ]
        )
    )
    repository = AsyncMock()
    repository.create.return_value = False
    password_hasher = Mock()
    password_hasher.hash.return_value = "hash-1"

    inserted_count = await seed_users(users_file, repository, password_hasher)

    repository.create.assert_awaited_once()
    assert inserted_count == 0
