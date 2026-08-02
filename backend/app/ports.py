"""Domain models and interfaces shared across application boundaries."""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    email: str
    hashed_password: str
