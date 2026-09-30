from __future__ import annotations

from app.core.database import APPLICATION_NAME, Database, build_connect_args
from tests.conftest import make_settings


def test_connect_args_default() -> None:
    args = build_connect_args(
        connect_timeout_seconds=5, statement_timeout_ms=30_000, use_pgbouncer=False
    )
    assert args["timeout"] == 5
    assert args["server_settings"] == {
        "application_name": APPLICATION_NAME,
        "statement_timeout": "30000",
    }
    assert "statement_cache_size" not in args


def test_connect_args_for_transaction_pooler() -> None:
    args = build_connect_args(connect_timeout_seconds=5, statement_timeout_ms=0, use_pgbouncer=True)
    assert args["statement_cache_size"] == 0
    assert "statement_timeout" not in args["server_settings"]
    name = args["prepared_statement_name_func"]()
    assert name.startswith("__asyncpg_") and name != args["prepared_statement_name_func"]()


async def test_database_from_settings_does_not_connect() -> None:
    # Port 1 on localhost is closed: creating the engine must still succeed.
    settings = make_settings(database_url="postgresql://u:p@127.0.0.1:1/nova", database_pool_size=3)
    database = Database.from_settings(settings)
    try:
        assert database.engine.url.drivername == "postgresql+asyncpg"
        assert database.engine.pool.size() == 3  # type: ignore[attr-defined]
    finally:
        await database.dispose()


async def test_pgbouncer_mode_disables_statement_cache_in_url() -> None:
    settings = make_settings(
        database_url="postgresql://u:p@127.0.0.1:6543/nova", database_use_pgbouncer=True
    )
    database = Database.from_settings(settings)
    try:
        assert database.engine.url.query["prepared_statement_cache_size"] == "0"
    finally:
        await database.dispose()
