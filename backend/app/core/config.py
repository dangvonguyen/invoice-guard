"""Control the app settings, including reading from a .env file."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Literal, get_args

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]

ModelProvider = Literal["openai", "anthropic"]

MODEL_PROVIDERS: tuple[str, ...] = get_args(ModelProvider)


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

    # Object storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    # "local" writes to disk (dev/CI)
    STORAGE_LOCAL_PATH: str = "./data/invoices"
    # S3-compatible object storage
    STORAGE_S3_ENDPOINT_URL: str | None = None
    STORAGE_S3_REGION: str = "us-east-1"
    STORAGE_S3_BUCKET: str | None = None
    STORAGE_S3_ACCESS_KEY_ID: str | None = None
    STORAGE_S3_SECRET_ACCESS_KEY: SecretStr | None = None
    STORAGE_S3_PREFIX: str = ""

    # API keys
    OPENAI_API_KEY: SecretStr
    ANTHROPIC_API_KEY: SecretStr

    # Embedding model
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Extraction settings
    EXTRACTION_PROVIDER: ModelProvider = "openai"
    EXTRACTION_MODEL: str = "gpt-5-mini"
    EXTRACTION_MAX_TOKENS: PositiveInt = 4096

    # Explanation generation
    GENERATION_PROVIDER: ModelProvider = "openai"
    GENERATION_MODEL: str = "gpt-5-mini"
    GENERATION_MAX_TOKENS: PositiveInt = 4096
    EXPLANATION_RETRIEVAL_TOP_K: PositiveInt = 5

    # Explanation golden-set judge (eval-only). Each unset value falls back to
    # the matching GENERATION_* value.
    JUDGE_PROVIDER: ModelProvider | None = None
    JUDGE_MODEL: str | None = None
    JUDGE_MAX_TOKENS: PositiveInt | None = None

    # Extraction reconciliation
    EXTRACTION_RECONCILE_INTERVAL_SECONDS: PositiveInt = 600
    EXTRACTION_RECONCILE_STALE_AFTER_SECONDS: PositiveInt = 1200
    EXTRACTION_RECONCILE_BATCH_LIMIT: PositiveInt = 100

    # Rule engine thresholds
    RULE_MAX_EXPENSE_AMOUNT: Decimal = Decimal("1000.00")
    RULE_MAX_EXPENSE_AGE_DAYS: PositiveInt = 90
    RULE_ALLOWED_CURRENCIES: str = "USD,EUR,GBP"
    RULE_RECONCILIATION_TOLERANCE: NonNegativeDecimal = Decimal("0.01")

    # Policy handbook ingestion
    POLICY_CHUNK_MIN_TOKENS: PositiveInt = 100
    POLICY_CHUNK_MAX_TOKENS: PositiveInt = 500
    POLICY_DOCUMENT_MAX_BYTES: PositiveInt = 50 * 1024 * 1024

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

    @model_validator(mode="after")
    def check_s3_storage_configured(self) -> Settings:
        """Require a bucket name before the app can use the S3 backend."""
        if self.STORAGE_BACKEND == "s3" and not self.STORAGE_S3_BUCKET:
            raise ValueError(
                "STORAGE_S3_BUCKET is required when STORAGE_BACKEND is 's3'"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the current settings."""
    return Settings()  # type: ignore
