"""Control the app settings, including reading from a .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def unwrap_secret(value: SecretStr | str) -> str:
    """Return the raw value from either a SecretStr or plain string."""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


class Settings(BaseSettings):
    """Application configuration.

    Configuration values are loaded from environment variables and, if present,
    from the `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_ignore_empty=True,
        extra="ignore",
    )

    API_ROOT: str = "/api"
    API_TITLE: str = "Invoice Guard API"

    CORS_ORIGINS: str = "*"

    # Setup the JWT authentication
    JWT_SECRET_KEY: SecretStr
    JWT_ACCESS_TOKEN_MINUTES: int = 30

    # Log configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_EXCLUDE_PATHS: str = "/health/live,/health/ready"

    # Setup the PostgreSQL database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @field_validator("API_ROOT")
    @classmethod
    def check_api_root(cls: type[Settings], value: str) -> str:
        """Normalize the API root path.

        Remove a trailing slash so that URL construction is consistent.
        """
        if value and value.endswith("/"):
            return value[:-1]
        return value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def check_jwt_secret(cls: type[Settings], value: SecretStr) -> SecretStr:
        """Require enough entropy for an HMAC signing key."""
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return value

    @field_validator("JWT_ACCESS_TOKEN_MINUTES")
    @classmethod
    def check_access_token_lifetime(cls: type[Settings], value: int) -> int:
        """Require access tokens to have a positive lifetime."""
        if value <= 0:
            raise ValueError("JWT_ACCESS_TOKEN_MINUTES must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the current settings."""
    return Settings()  # type: ignore
