"""Queries about the database itself (connectivity, migration state)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import APP_SCHEMA


class SystemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ping(self) -> None:
        await self.session.execute(text("SELECT 1"))

    async def current_migration_revision(self) -> str | None:
        """Alembic revision applied to the database, or None if never migrated."""
        table = await self.session.scalar(
            text("SELECT to_regclass(:name)"), {"name": f"{APP_SCHEMA}.alembic_version"}
        )
        if table is None:
            return None
        revision = await self.session.scalar(
            text(f'SELECT version_num FROM "{APP_SCHEMA}".alembic_version LIMIT 1')  # noqa: S608 - constant schema name
        )
        return str(revision) if revision is not None else None
