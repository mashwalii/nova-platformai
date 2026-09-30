"""Management commands: ``uv run python -m app.cli <command>``.

Commands:
  config    Show the effective configuration (secrets hidden)
  check-db  Test the database connection and show the migration revision
  openapi   Export the OpenAPI schema (used to generate frontend types)
  seed      Load development sample data (development/test databases only)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.repositories.system import SystemRepository


def cmd_config(settings: Settings) -> int:
    data = settings.model_dump(mode="json")
    data["database_url"] = settings.masked_database_url()
    if settings.database_migration_url is not None:
        data["database_migration_url"] = "(set, hidden)"
    print(json.dumps(data, indent=2))
    return 0


async def _check_db(settings: Settings) -> int:
    if not settings.database_configured:
        print("DATABASE_URL is not set. See backend/.env.example.", file=sys.stderr)
        return 1
    database = Database.from_settings(settings)
    try:
        async with database.session() as session:
            repository = SystemRepository(session)
            await repository.ping()
            revision = await repository.current_migration_revision()
    except Exception as exc:
        print(f"Database connection FAILED ({type(exc).__name__}).", file=sys.stderr)
        print(f"Target: {settings.masked_database_url()}", file=sys.stderr)
        return 1
    finally:
        await database.dispose()
    print(f"Database connection OK: {settings.masked_database_url()}")
    print(f"Migration revision: {revision or 'none (run: uv run alembic upgrade head)'}")
    return 0


async def _seed(settings: Settings, path: Path) -> int:
    from app.seed import load_seed, read_seed_file

    if settings.is_deployed:
        print(
            f"Refusing to load sample data into a {settings.app_env.value} database.",
            file=sys.stderr,
        )
        return 1
    if not settings.database_configured:
        print("DATABASE_URL is not set. See backend/.env.example.", file=sys.stderr)
        return 1
    data = read_seed_file(path)
    database = Database.from_settings(settings)
    try:
        async with database.session() as session:
            counts = await load_seed(session, data)
            await session.commit()
    finally:
        await database.dispose()
    print(f"Seed data loaded into {settings.masked_database_url()}")
    for table, rows in sorted(counts.items()):
        print(f"  {table:<22} {rows:>4}")
    return 0


def cmd_openapi(output: str | None) -> int:
    from app.main import create_app

    # Docs are forced on so the schema exists even in production mode.
    # No database connection is opened: building the app does not connect.
    settings = get_settings().model_copy(update={"docs_enabled": True})
    schema = create_app(settings).openapi()
    text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
        print(f"OpenAPI schema written to {output}")
    else:
        sys.stdout.write(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="NOVA backend tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("config", help="show effective configuration (secrets hidden)")
    sub.add_parser("check-db", help="test the database connection")
    openapi = sub.add_parser("openapi", help="export the OpenAPI schema")
    openapi.add_argument("--output", "-o", help="file to write (default: print)")
    seed = sub.add_parser("seed", help="load development sample data")
    seed.add_argument("--file", help="seed JSON file (default: the built-in dev seed)")
    args = parser.parse_args(argv)

    if args.command == "config":
        return cmd_config(get_settings())
    if args.command == "check-db":
        return asyncio.run(_check_db(get_settings()))
    if args.command == "openapi":
        return cmd_openapi(args.output)
    if args.command == "seed":
        from app.seed import DEV_SEED_FILE

        return asyncio.run(_seed(get_settings(), Path(args.file) if args.file else DEV_SEED_FILE))
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
