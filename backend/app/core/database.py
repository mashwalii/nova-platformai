"""Database connection layer (SQLAlchemy 2 async + asyncpg).

``Database`` owns the connection pool. Creating it does not open any
connection — the first query does — so the API can start (and report its
status on ``/ready``) even when the database is unreachable.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

APPLICATION_NAME = "nova-api"


def build_connect_args(
    *,
    connect_timeout_seconds: float,
    statement_timeout_ms: int,
    use_pgbouncer: bool,
) -> dict[str, Any]:
    """asyncpg connection arguments."""
    server_settings = {"application_name": APPLICATION_NAME}
    if statement_timeout_ms > 0:
        server_settings["statement_timeout"] = str(statement_timeout_ms)
    connect_args: dict[str, Any] = {
        "timeout": connect_timeout_seconds,
        "server_settings": server_settings,
    }
    if use_pgbouncer:
        # Transaction-mode poolers (e.g. Supabase port 6543) can't reuse
        # prepared statements across connections.
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid.uuid4()}__"
    return connect_args


class Database:
    """Holds the async engine and session factory for one application instance."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self._sessionmaker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> Database:
        url: URL = settings.async_database_url()
        if settings.database_use_pgbouncer:
            url = url.update_query_dict({"prepared_statement_cache_size": "0"})
        engine = create_async_engine(
            url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=False,  # SQL logging is routed through the logging config instead
            connect_args=build_connect_args(
                connect_timeout_seconds=settings.database_connect_timeout_seconds,
                statement_timeout_ms=settings.database_statement_timeout_ms,
                use_pgbouncer=settings.database_use_pgbouncer,
            ),
        )
        return cls(engine)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """A session for one unit of work.

        Changes are only saved when the caller commits (``await session.commit()``);
        anything uncommitted is rolled back when the block exits.
        """
        async with self._sessionmaker() as session:
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        """Close all pooled connections (called on shutdown)."""
        await self.engine.dispose()
