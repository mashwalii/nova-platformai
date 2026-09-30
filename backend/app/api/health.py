"""Infrastructure probes.

These live outside ``/v1`` on purpose: hosting platforms and uptime monitors
expect stable, unversioned paths.

* ``GET /health`` — liveness: the process is up. Never touches the database.
* ``GET /ready``  — readiness: dependencies (the database) are reachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import HealthServiceDep
from app.schemas.system import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
async def health(service: HealthServiceDep) -> HealthResponse:
    return service.liveness()


@router.get(
    "/ready",
    summary="Readiness check",
    responses={503: {"model": ReadinessResponse, "description": "A dependency is unavailable"}},
)
async def ready(service: HealthServiceDep, response: Response) -> ReadinessResponse:
    report = await service.readiness()
    if report.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
