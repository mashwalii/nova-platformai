"""Application configuration.

All settings come from environment variables (optionally loaded from
``backend/.env`` for local development). Secrets are stored as ``SecretStr`` so
they are never printed in logs, error messages, or ``repr()`` output.

See ``backend/.env.example`` for the full list of variables.
"""

from __future__ import annotations

import re
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

DEVELOPMENT_CORS_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_ORIGIN_PATTERN = re.compile(r"^https?://[A-Za-z0-9.\-]+(:\d{1,5})?$")
_POSTGRES_SCHEMES = {"postgres", "postgresql", "postgresql+asyncpg"}


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def normalize_database_url(raw: str) -> URL:
    """Convert any PostgreSQL URL into one usable by SQLAlchemy's asyncpg driver.

    Accepts ``postgres://``, ``postgresql://`` and ``postgresql+asyncpg://``
    (the formats Supabase and most hosts provide) and translates libpq's
    ``sslmode`` query parameter into asyncpg's ``ssl`` parameter.
    """
    try:
        url = make_url(raw.strip())
    except ArgumentError as exc:
        raise ValueError("Database URL is not a valid URL") from exc
    if url.drivername not in _POSTGRES_SCHEMES:
        raise ValueError("Database URL must start with postgresql:// (or postgres://)")
    query = dict(url.query)
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    return url.set(drivername="postgresql+asyncpg", query=query)


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,  # `NAME=` (blank) means "use the default"
        hide_input_in_errors=True,  # never print raw values (e.g. passwords) in errors
    )

    # --- Application -------------------------------------------------------
    app_name: str = "NOVA AI API"
    app_env: Environment = Environment.DEVELOPMENT
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # --- Logging -----------------------------------------------------------
    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat | None = None  # default: console in development, json elsewhere

    # --- HTTP / security ---------------------------------------------------
    cors_allow_origins: Annotated[list[str] | None, NoDecode] = None
    cors_allow_origin_regex: str | None = None
    docs_enabled: bool | None = None  # default: on everywhere except production
    max_request_body_bytes: int = Field(default=1_048_576, ge=1_024)

    # --- Database ----------------------------------------------------------
    database_url: SecretStr | None = None
    database_migration_url: SecretStr | None = None
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=5, ge=0, le=100)
    database_pool_timeout_seconds: float = Field(default=10.0, gt=0)
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    database_statement_timeout_ms: int = Field(default=30_000, ge=0)
    database_use_pgbouncer: bool = False
    database_echo: bool = False

    health_check_timeout_seconds: float = Field(default=3.0, gt=0)

    # --- Validators ----------------------------------------------------------

    @field_validator("database_url", "database_migration_url", mode="before")
    @classmethod
    def _empty_secret_is_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url", "database_migration_url")
    @classmethod
    def _validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            normalize_database_url(value.get_secret_value())
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("cors_allow_origins")
    @classmethod
    def _validate_origins(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for origin in value:
            origin = origin.rstrip("/")
            if origin != "*" and not _ORIGIN_PATTERN.match(origin):
                raise ValueError(
                    f"Invalid CORS origin {origin!r}: use the form https://example.com "
                    "(scheme + host + optional port, no path)"
                )
            cleaned.append(origin)
        return cleaned

    @field_validator("cors_allow_origin_regex")
    @classmethod
    def _validate_origin_regex(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"CORS_ALLOW_ORIGIN_REGEX is not a valid regex: {exc}") from exc
        return value

    @model_validator(mode="after")
    def _apply_environment_defaults(self) -> Settings:
        deployed = self.app_env in (Environment.STAGING, Environment.PRODUCTION)

        if self.cors_allow_origins is None:
            self.cors_allow_origins = [] if deployed else list(DEVELOPMENT_CORS_ORIGINS)
        if self.log_format is None:
            is_dev = self.app_env == Environment.DEVELOPMENT
            self.log_format = LogFormat.CONSOLE if is_dev else LogFormat.JSON
        if self.docs_enabled is None:
            self.docs_enabled = self.app_env != Environment.PRODUCTION

        if deployed:
            if self.database_url is None:
                raise ValueError(f"DATABASE_URL is required when APP_ENV={self.app_env.value}")
            if "*" in self.cors_allow_origins:
                raise ValueError(
                    "CORS_ALLOW_ORIGINS must list explicit origins "
                    f"when APP_ENV={self.app_env.value}"
                )
        return self

    # --- Derived values ------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_deployed(self) -> bool:
        return self.app_env in (Environment.STAGING, Environment.PRODUCTION)

    @property
    def database_configured(self) -> bool:
        return self.database_url is not None

    def async_database_url(self) -> URL:
        """Normalized runtime database URL (raises if not configured)."""
        if self.database_url is None:
            raise RuntimeError("DATABASE_URL is not configured")
        return normalize_database_url(self.database_url.get_secret_value())

    def async_migration_database_url(self) -> URL:
        """URL for migrations: DATABASE_MIGRATION_URL, falling back to DATABASE_URL."""
        secret = self.database_migration_url or self.database_url
        if secret is None:
            raise RuntimeError("Neither DATABASE_MIGRATION_URL nor DATABASE_URL is configured")
        return normalize_database_url(secret.get_secret_value())

    def masked_database_url(self) -> str | None:
        """Database URL with the password hidden — safe to log or display."""
        if self.database_url is None:
            return None
        return self.async_database_url().render_as_string(hide_password=True)


@lru_cache
def get_settings() -> Settings:
    """Settings loaded once from the environment (and ``backend/.env``)."""
    return Settings()
