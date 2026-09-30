"""API information for version 1 (served at ``GET /v1``)."""

from __future__ import annotations

from app import __version__
from app.api.deps import AppSettings
from app.schemas.system import ApiInfoResponse


async def api_info(settings: AppSettings) -> ApiInfoResponse:
    return ApiInfoResponse(
        name=settings.app_name,
        version=__version__,
        environment=settings.app_env.value,
        docs_url="/docs" if settings.docs_enabled else None,
    )
