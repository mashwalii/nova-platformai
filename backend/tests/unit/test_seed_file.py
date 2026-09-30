"""The development seed file is valid and consistent (no database needed)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app import cli
from app.core.config import Settings
from app.models.enums import OpportunityType
from app.seed import DEV_SEED_FILE, read_seed_file, seed_id
from app.seed.schema import SeedData


def _raw() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DEV_SEED_FILE.read_text(encoding="utf-8"))
    return data


def test_seed_file_is_valid() -> None:
    data = read_seed_file()
    assert len(data.articles) == 7  # mirrors the frontend's sample articles
    assert len(data.courses) == 6
    assert {o.opportunity_type for o in data.opportunities} == set(OpportunityType)
    assert data.papers and data.tools and data.users and data.daily_briefs


def test_every_article_has_bilingual_brief() -> None:
    for article in read_seed_file().articles:
        assert set(article.brief) == {"en", "ar"}
        assert article.title.en and article.title.ar


def test_seed_users_are_fake() -> None:
    for user in read_seed_file().users:
        assert user.email.endswith("@example.com")


def test_unknown_reference_is_rejected() -> None:
    raw = _raw()
    raw["articles"][0]["category"] = "does-not-exist"
    with pytest.raises(ValidationError, match="unknown category 'does-not-exist'"):
        SeedData.model_validate(raw)


def test_duplicate_slug_is_rejected() -> None:
    raw = _raw()
    raw["tags"].append(raw["tags"][0])
    with pytest.raises(ValidationError, match="duplicate tag slug"):
        SeedData.model_validate(raw)


def test_unknown_field_is_rejected() -> None:
    raw = _raw()
    raw["sources"][0]["api_key"] = "should-not-be-here"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SeedData.model_validate(raw)


def test_seed_ids_are_stable() -> None:
    assert seed_id("content", "article:benchmark") == seed_id("content", "article:benchmark")
    assert seed_id("content", "article:benchmark") != seed_id("content", "article:policy")


def test_seed_command_refuses_production(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/nova")
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    assert cli.main(["seed"]) == 1
    assert "Refusing to load sample data" in capsys.readouterr().err
