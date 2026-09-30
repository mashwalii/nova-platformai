"""FastAPI application factory.

Run with ``uv run python -m app`` (see ``app/__main__.py``) or
``uvicorn app.main:create_app --factory``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.api.v1.router import API_V1_PREFIX, api_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    REQUEST_ID_HEADER,
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)

logger = logging.getLogger("nova.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    logger.info(
        "starting %s %s",
        settings.app_name,
        __version__,
        extra={
            "environment": settings.app_env.value,
            "database": settings.masked_database_url() or "not configured",
            "docs_enabled": settings.docs_enabled,
        },
    )
    yield
    database: Database | None = app.state.database
    if database is not None:
        await database.dispose()
    logger.info("shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fully configured application instance."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Backend API for the NOVA AI information platform.",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{API_V1_PREFIX}/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    # The pool is created lazily: no connection is opened until the first query.
    app.state.database = Database.from_settings(settings) if settings.database_configured else None

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)

    # Middleware: the LAST one added runs FIRST (outermost).
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins or [],
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=False,  # the API uses bearer tokens, not cookies
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Accept-Language",
            REQUEST_ID_HEADER,
        ],
        expose_headers=[REQUEST_ID_HEADER],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_deployed)

    return app
