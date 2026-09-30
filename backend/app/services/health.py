"""Health and readiness checks."""

from __future__ import annotations

import asyncio
import logging
import time

from app import __version__
from app.core.config import Settings
from app.core.database import Database
from app.repositories.system import SystemRepository
from app.schemas.system import DependencyCheck, HealthResponse, ReadinessResponse

logger = logging.getLogger("nova.health")


class HealthService:
    def __init__(self, settings: Settings, database: Database | None) -> None:
        self.settings = settings
        self.database = database

    def liveness(self) -> HealthResponse:
        """The process is running (no dependencies are checked)."""
        return HealthResponse(service=self.settings.app_name, version=__version__)

    async def readiness(self) -> ReadinessResponse:
        """Whether the service can handle real traffic (dependencies reachable)."""
        database = await self._check_database()
        ready = database.status == "ok"
        return ReadinessResponse(
            status="ok" if ready else "unavailable", checks={"database": database}
        )

    async def _check_database(self) -> DependencyCheck:
        if self.database is None:
            return DependencyCheck(status="not_configured", detail="DATABASE_URL is not set")

        start = time.perf_counter()
        try:
            async with asyncio.timeout(self.settings.health_check_timeout_seconds):
                async with self.database.session() as session:
                    repository = SystemRepository(session)
                    await repository.ping()
                    revision = await repository.current_migration_revision()
        except Exception as exc:
            # Details stay in the server log; clients only learn that it failed.
            logger.warning("database health check failed", extra={"error_type": type(exc).__name__})
            return DependencyCheck(status="error", detail="database unreachable")

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(status="ok", latency_ms=latency_ms, migration_revision=revision)
