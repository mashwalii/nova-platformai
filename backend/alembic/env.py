"""Alembic migration environment (async, PostgreSQL).

* Reads the database URL from settings (DATABASE_MIGRATION_URL, else DATABASE_URL);
  callers may override it with ``config.attributes["database_url"]`` (used by tests).
* Creates the ``app`` schema if needed and keeps Alembic's version table there.
* Only compares objects in the ``app`` schema, so Supabase's own schemas
  (auth, storage, …) are never touched by autogenerate.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import URL, Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.elements import conv

import app.models  # noqa: F401 - registers every model on Base.metadata
from app.core.config import get_settings, normalize_database_url
from app.core.database import build_connect_args
from app.models.base import APP_SCHEMA, Base

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> URL:
    override = config.attributes.get("database_url")
    if override:
        return normalize_database_url(str(override))
    return get_settings().async_migration_database_url()


def _include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    if type_ == "schema":
        return name == APP_SCHEMA
    return True


def _render_item(type_: str, obj: Any, autogen_context: Any) -> Any:
    """Customise how autogenerate writes some objects into migration files.

    Our "enum" columns are VARCHAR + a CHECK constraint (see app/models/enums.py).
    Alembic would otherwise write the CHECK constraint several times (once via the
    column type, again as table constraints), so the column is rendered as a
    plain String and only the named table-level constraint is kept.

    Returns a string (custom rendering), False (Alembic's default), or None to
    omit a constraint (supported by Alembic, though not in its type hints).
    """
    if type_ == "type" and isinstance(obj, sa.Enum) and not obj.native_enum:
        return f"sa.String(length={obj.length})"
    if type_ == "check" and isinstance(obj, sa.CheckConstraint):
        name = obj.name
        if name is not None and not isinstance(name, conv) and getattr(obj, "_type_bound", False):
            return None  # skip: unconverted duplicate of a type-bound constraint
    return False


def _configure(**kwargs: Any) -> None:
    context.configure(
        target_metadata=target_metadata,
        version_table_schema=APP_SCHEMA,
        include_schemas=True,
        include_name=_include_name,
        compare_type=True,
        render_item=_render_item,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (``alembic upgrade head --sql``)."""
    _configure(
        url=_database_url().render_as_string(hide_password=False),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.execute(f'CREATE SCHEMA IF NOT EXISTS "{APP_SCHEMA}"')
        context.run_migrations()


def _run_sync_migrations(connection: Connection) -> None:
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{APP_SCHEMA}"'))
    connection.commit()
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    settings = get_settings()
    engine = create_async_engine(
        _database_url(),
        poolclass=pool.NullPool,
        connect_args=build_connect_args(
            connect_timeout_seconds=settings.database_connect_timeout_seconds,
            statement_timeout_ms=0,  # migrations may legitimately take long
            use_pgbouncer=False,  # use a direct/session connection for migrations
        ),
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_sync_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
