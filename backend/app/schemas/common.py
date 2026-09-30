"""Shared API response shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["The requested resource was not found."])
    details: Any = None
    request_id: str | None = Field(default=None, examples=["3f2b8c1e9d7a4f6b8e0c2d4a6b8c0e1f"])


class ErrorResponse(BaseModel):
    """Shape of every error returned by the API."""

    error: ErrorBody
