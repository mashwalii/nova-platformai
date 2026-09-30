"""Shared test fixtures.

* Unit and API tests need nothing external.
* Tests marked ``@pytest.mark.db`` need a THROWAWAY PostgreSQL database given in
  ``TEST_DATABASE_URL`` (its name must contain "test"); they are skipped otherwise.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import BACKEND_DIR, Settings, normalize_database_url
from app.core.database import Database
from app.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip() or None


def make_settings(**overrides: Any) -> Settings:
    """Settings for tests: never reads backend/.env, quiet logs."""
    values: dict[str, Any] = {"app_env": "test", "log_level": "WARNING"}
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop variables from the developer's shell leaking into test settings."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if TEST_DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


# --- API client ----------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    database: Database | None = app.state.database
    if database is not None:
        await database.dispose()


# --- Database ------------------------------------------------------------------


def alembic_head() -> str:
    """Latest migration revision in alembic/versions."""
    from alembic.script import ScriptDirectory

    head = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini"))).get_current_head()
    assert head is not None
    return head


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


async def _reset_app_schema(database_url: str) -> None:
    engine = create_async_engine(normalize_database_url(database_url), poolclass=pool.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS app CASCADE"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    """A freshly migrated test database (schema `app` dropped and rebuilt once per run)."""
    from alembic import command

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    database_name = normalize_database_url(TEST_DATABASE_URL).database or ""
    if "test" not in database_name.lower():
        pytest.exit(
            f"Refusing to run: TEST_DATABASE_URL database {database_name!r} does not "
            "contain 'test'. The tests delete data — use a throwaway database.",
            returncode=2,
        )
    asyncio.run(_reset_app_schema(TEST_DATABASE_URL))
    command.upgrade(alembic_config(TEST_DATABASE_URL), "head")
    return TEST_DATABASE_URL


@pytest.fixture
async def database(database_url: str) -> AsyncIterator[Database]:
    db = Database.from_settings(make_settings(database_url=database_url))
    yield db
    await db.dispose()
