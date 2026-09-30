from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import cli
from app.core.config import Settings


@pytest.fixture(autouse=True)
def _settings_without_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Commands read settings from environment variables only (no backend/.env)."""
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))


def test_config_command_hides_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://nova:topsecret@db.example.com/nova")
    assert cli.main(["config"]) == 0
    output = capsys.readouterr().out
    assert "topsecret" not in output
    assert json.loads(output)["database_url"].startswith("postgresql+asyncpg://nova:***@")


def test_check_db_without_database_url_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    assert cli.main(["check-db"]) == 1
    assert "DATABASE_URL is not set" in capsys.readouterr().err


def test_openapi_command_writes_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    target = tmp_path / "openapi.json"
    assert cli.main(["openapi", "--output", str(target)]) == 0
    schema = json.loads(target.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "NOVA AI API"
    assert {"/health", "/ready", "/v1"} <= set(schema["paths"])
