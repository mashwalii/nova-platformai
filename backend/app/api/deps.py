"""FastAPI dependencies shared by all routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import Database
from app.core.errors import ServiceUnavailableError
from app.services.health import HealthService


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database | None:
    database: Database | None = request.app.state.database
    return database


async def get_db_session(
    database: Annotated[Database | None, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    """One database session per request. Routes needing the database use ``DbSession``."""
    if database is None:
        raise ServiceUnavailableError(
            "The database is not configured.", code="database_not_configured"
        )
    async with database.session() as session:
        yield session


def get_health_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
    database: Annotated[Database | None, Depends(get_database)],
) -> HealthService:
    return HealthService(settings, database)


AppSettings = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
