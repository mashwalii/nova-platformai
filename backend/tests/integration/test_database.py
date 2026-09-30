"""Tests against a real PostgreSQL database (need TEST_DATABASE_URL)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import MetaData, String, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app import cli
from app.core.config import Settings
from app.core.database import Database
from app.main import create_app
from app.models.base import APP_SCHEMA, TimestampMixin, UUIDPrimaryKeyMixin
from app.repositories.base import BaseRepository
from app.repositories.system import SystemRepository
from tests.conftest import alembic_head, make_settings

pytestmark = pytest.mark.db


class _TestBase(DeclarativeBase):
    """Separate metadata so test tables never leak into real migrations."""

    metadata = MetaData(schema=APP_SCHEMA)


class Widget(UUIDPrimaryKeyMixin, TimestampMixin, _TestBase):
    __tablename__ = "test_widgets"

    name: Mapped[str] = mapped_column(String(50))


class WidgetRepository(BaseRepository[Widget]):
    model = Widget


@pytest.fixture
async def widget_table(database: Database) -> AsyncIterator[None]:
    async with database.engine.begin() as connection:
        await connection.run_sync(_TestBase.metadata.create_all)
    yield
    async with database.engine.begin() as connection:
        await connection.run_sync(_TestBase.metadata.drop_all)


# --- Health against a real database ----------------------------------------------


async def test_ready_with_database(database_url: str) -> None:
    app = create_app(make_settings(database_url=database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ready")
    await app.state.database.dispose()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["database"]["migration_revision"] == alembic_head()
    assert body["checks"]["database"]["latency_ms"] >= 0


async def test_system_repository(database: Database) -> None:
    async with database.session() as session:
        repository = SystemRepository(session)
        await repository.ping()
        assert await repository.current_migration_revision() == alembic_head()


async def test_connection_uses_application_name(database: Database) -> None:
    async with database.session() as session:
        name = await session.scalar(text("SELECT current_setting('application_name')"))
    assert name == "nova-api"


# --- Repository & sessions -------------------------------------------------------


@pytest.mark.usefixtures("widget_table")
async def test_base_repository_crud(database: Database) -> None:
    async with database.session() as session:
        repository = WidgetRepository(session)
        created = [await repository.add(Widget(name=f"w{i}")) for i in range(3)]
        await session.commit()

    assert all(isinstance(w.id, uuid.UUID) for w in created)
    assert all(w.created_at is not None for w in created)

    async with database.session() as session:
        repository = WidgetRepository(session)
        assert await repository.count() == 3
        fetched = await repository.get(created[0].id)
        assert fetched is not None and fetched.name == "w0"
        page = await repository.get_many(limit=2)
        assert len(page) == 2
        rest = await repository.get_many(limit=2, offset=2)
        assert len(rest) == 1
        await repository.delete(fetched)
        await session.commit()

    async with database.session() as session:
        repository = WidgetRepository(session)
        assert await repository.count() == 2
        assert await repository.get(created[0].id) is None


@pytest.mark.usefixtures("widget_table")
@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (101, 0), (10, -1)])
async def test_get_many_rejects_bad_paging(database: Database, limit: int, offset: int) -> None:
    async with database.session() as session:
        with pytest.raises(ValueError):
            await WidgetRepository(session).get_many(limit=limit, offset=offset)


@pytest.mark.usefixtures("widget_table")
async def test_session_rolls_back_on_error(database: Database) -> None:
    with pytest.raises(RuntimeError):
        async with database.session() as session:
            await WidgetRepository(session).add(Widget(name="never saved"))
            raise RuntimeError("boom")

    async with database.session() as session:
        names = (await session.scalars(select(Widget.name))).all()
    assert "never saved" not in names


@pytest.mark.usefixtures("widget_table")
async def test_uncommitted_changes_are_discarded(database: Database) -> None:
    async with database.session() as session:
        await WidgetRepository(session).add(Widget(name="forgotten"))
        # no commit

    async with database.session() as session:
        assert await WidgetRepository(session).count() == 0


# --- Migration helpers -----------------------------------------------------------


@pytest.mark.usefixtures("widget_table")
async def test_set_updated_at_trigger_function(database: Database) -> None:
    async with database.session() as session:
        await session.execute(
            text(
                "CREATE TRIGGER test_widgets_updated_at BEFORE UPDATE ON app.test_widgets "
                "FOR EACH ROW EXECUTE FUNCTION app.set_updated_at()"
            )
        )
        widget = await WidgetRepository(session).add(Widget(name="before"))
        await session.commit()
        original = widget.updated_at

    await asyncio.sleep(0.01)
    async with database.session() as session:
        # A raw UPDATE (like an edit in the Supabase Table Editor) still bumps updated_at.
        await session.execute(
            text("UPDATE app.test_widgets SET name = 'after' WHERE id = :id"), {"id": widget.id}
        )
        await session.commit()
        updated = await session.scalar(
            text("SELECT updated_at FROM app.test_widgets WHERE id = :id"), {"id": widget.id}
        )
    assert updated is not None and updated > original


def test_migrations_downgrade_and_upgrade(database_url: str) -> None:
    from alembic import command

    from tests.conftest import alembic_config

    config = alembic_config(database_url)
    command.downgrade(config, "base")
    assert asyncio.run(_function_exists(database_url)) is False
    command.upgrade(config, "head")
    assert asyncio.run(_function_exists(database_url)) is True


def test_models_match_migrations(database_url: str) -> None:
    """Fails if a model changed without a matching migration (``alembic check``)."""
    from alembic import command

    from tests.conftest import alembic_config

    command.check(alembic_config(database_url))


async def _function_exists(database_url: str) -> bool:
    database = Database.from_settings(make_settings(database_url=database_url))
    try:
        async with database.session() as session:
            result = await session.scalar(
                text("SELECT to_regprocedure('app.set_updated_at()') IS NOT NULL")
            )
    finally:
        await database.dispose()
    return bool(result)


# --- CLI -------------------------------------------------------------------------


def test_cli_check_db(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    assert cli.main(["check-db"]) == 0
    output = capsys.readouterr().out
    assert "Database connection OK" in output
    assert f"Migration revision: {alembic_head()}" in output
