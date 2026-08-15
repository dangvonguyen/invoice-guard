"""Control the app settings, including reading from a .env file."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]


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
    JWT_ACCESS_TOKEN_MINUTES: PositiveInt = 30

    # Log configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_EXCLUDE_PATHS: str = "/health/live,/health/ready"

    # Setup the PostgreSQL database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Redis - rate limiting
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Invoice upload constraints
    UPLOAD_MAX_BYTES: PositiveInt = 10 * 1024 * 1024
    UPLOAD_RATE_LIMIT: PositiveInt = 20
    UPLOAD_RATE_LIMIT_WINDOW_SECONDS: PositiveInt = 60

    # Local-disk object storage. Dev/CI only - swap for an S3-compatible
    # adapter behind the same StorageClient protocol before deploying.
    STORAGE_LOCAL_PATH: str = "./data/invoices"

    # Extraction model
    OPENAI_API_KEY: SecretStr
    OPENAI_EXTRACTION_MODEL: str = "gpt-5-mini"

    # Extraction reconciliation
    EXTRACTION_RECONCILE_INTERVAL_SECONDS: PositiveInt = 600
    EXTRACTION_RECONCILE_STALE_AFTER_SECONDS: PositiveInt = 1200
    EXTRACTION_RECONCILE_BATCH_LIMIT: PositiveInt = 100

    # Rule engine thresholds
    RULE_MAX_EXPENSE_AMOUNT: Decimal = Decimal("1000.00")
    RULE_MAX_EXPENSE_AGE_DAYS: PositiveInt = 90
    RULE_ALLOWED_CURRENCIES: str = "USD,EUR,GBP"
    RULE_RECONCILIATION_TOLERANCE: NonNegativeDecimal = Decimal("0.01")

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


@lru_cache
def get_settings() -> Settings:
    """Return the current settings."""
    return Settings()  # type: ignore
