"""All routes of API version 1, mounted under ``/v1``.

To add a feature: create ``app/api/v1/endpoints/<feature>.py`` with its own
``APIRouter`` and include it here with a prefix, e.g.
``api_router.include_router(news.router, prefix="/news")``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import meta
from app.schemas.common import ErrorResponse

API_V1_PREFIX = "/v1"

api_router = APIRouter(
    prefix=API_V1_PREFIX,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Unexpected error"},
    },
)
# `GET /v1` itself (a route with an empty path must be added directly).
api_router.add_api_route(
    "", meta.api_info, methods=["GET"], summary="API information", tags=["meta"]
)
