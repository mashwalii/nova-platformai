"""Response shapes for health checks and API information."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = Field(examples=["NOVA AI API"])
    version: str = Field(examples=["0.1.0"])


class DependencyCheck(BaseModel):
    status: Literal["ok", "error", "not_configured"]
    latency_ms: float | None = None
    detail: str | None = None
    migration_revision: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    checks: dict[str, DependencyCheck]


class ApiInfoResponse(BaseModel):
    name: str
    api_version: Literal["v1"] = "v1"
    version: str
    environment: str
    docs_url: str | None
