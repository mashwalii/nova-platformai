from __future__ import annotations

import tomllib

import pytest
from pydantic import ValidationError

from app import __version__
from app.core.config import (
    BACKEND_DIR,
    DEVELOPMENT_CORS_ORIGINS,
    Environment,
    LogFormat,
    Settings,
    normalize_database_url,
)
from tests.conftest import make_settings

FAKE_DB = "postgresql://nova:s3cret-pw@db.example.com:5432/nova"


def test_development_defaults() -> None:
    settings = make_settings(app_env="development")
    assert settings.app_env == Environment.DEVELOPMENT
    assert settings.cors_allow_origins == DEVELOPMENT_CORS_ORIGINS
    assert settings.log_format == LogFormat.CONSOLE
    assert settings.docs_enabled is True
    assert settings.database_configured is False
    assert settings.is_deployed is False


def test_non_development_defaults_to_json_logs() -> None:
    assert make_settings(app_env="test").log_format == LogFormat.JSON


def test_production_requires_database_url() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        make_settings(app_env="production")


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="explicit origins"):
        make_settings(app_env="production", database_url=FAKE_DB, cors_allow_origins="*")


def test_production_defaults_are_locked_down() -> None:
    settings = make_settings(app_env="production", database_url=FAKE_DB)
    assert settings.cors_allow_origins == []
    assert settings.docs_enabled is False
    assert settings.is_production and settings.is_deployed


def test_cors_origins_parsed_from_comma_separated_string() -> None:
    settings = make_settings(cors_allow_origins="https://nova.example.com/, http://localhost:8080")
    assert settings.cors_allow_origins == ["https://nova.example.com", "http://localhost:8080"]


@pytest.mark.parametrize("origin", ["nova.example.com", "https://nova.example.com/path", "ftp://x"])
def test_invalid_cors_origin_rejected(origin: str) -> None:
    with pytest.raises(ValidationError, match="Invalid CORS origin"):
        make_settings(cors_allow_origins=origin)


def test_invalid_origin_regex_rejected() -> None:
    with pytest.raises(ValidationError, match="not a valid regex"):
        make_settings(cors_allow_origin_regex="(unclosed")


def test_blank_environment_values_use_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "LOG_FORMAT", "DOCS_ENABLED", "CORS_ALLOW_ORIGINS"):
        monkeypatch.setenv(name, "")
    settings = Settings(_env_file=None, app_env="development")
    assert settings.database_url is None
    assert settings.log_format == LogFormat.CONSOLE
    assert settings.docs_enabled is True
    assert settings.cors_allow_origins == DEVELOPMENT_CORS_ORIGINS


def test_env_example_file_is_valid() -> None:
    """The committed template must load cleanly and give development defaults."""
    settings = Settings(_env_file=BACKEND_DIR / ".env.example")
    assert settings.app_env == Environment.DEVELOPMENT
    assert settings.database_url is None
    assert settings.cors_allow_origins == DEVELOPMENT_CORS_ORIGINS


def test_secrets_never_appear_in_output() -> None:
    settings = make_settings(database_url=FAKE_DB)
    for rendered in (repr(settings), str(settings), str(settings.model_dump())):
        assert "s3cret-pw" not in rendered
    masked = settings.masked_database_url()
    assert masked is not None
    assert "s3cret-pw" not in masked
    assert "db.example.com" in masked


@pytest.mark.parametrize(
    ("raw", "expected_driver"),
    [
        ("postgres://u:p@h/db", "postgresql+asyncpg"),
        ("postgresql://u:p@h/db", "postgresql+asyncpg"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg"),
    ],
)
def test_database_url_normalized_to_asyncpg(raw: str, expected_driver: str) -> None:
    assert normalize_database_url(raw).drivername == expected_driver


def test_sslmode_translated_for_asyncpg() -> None:
    url = normalize_database_url("postgresql://u:p@h:5432/db?sslmode=require")
    assert dict(url.query) == {"ssl": "require"}


@pytest.mark.parametrize("raw", ["mysql://u:p@h/db", "not a url"])
def test_invalid_database_url_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(database_url=raw)


def test_migration_url_falls_back_to_database_url() -> None:
    settings = make_settings(database_url=FAKE_DB)
    assert settings.async_migration_database_url() == settings.async_database_url()
    other = "postgresql://admin:pw@db.example.com:5432/nova"
    settings = make_settings(database_url=FAKE_DB, database_migration_url=other)
    assert settings.async_migration_database_url().username == "admin"


def test_async_database_url_requires_configuration() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        make_settings().async_database_url()


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((BACKEND_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == __version__


@pytest.mark.parametrize(
    "overrides",
    [
        # field-level error (unsupported scheme)
        {"database_url": "mysql://nova:leaky-pw@db.example.com/nova"},
        # model-level error (wildcard CORS in production) with a valid secret present
        {"app_env": "production", "database_url": FAKE_DB, "cors_allow_origins": "*"},
    ],
)
def test_validation_errors_do_not_reveal_secrets(overrides: dict[str, str]) -> None:
    with pytest.raises(ValidationError) as excinfo:
        make_settings(**overrides)
    message = str(excinfo.value)
    assert "leaky-pw" not in message
    assert "s3cret-pw" not in message
