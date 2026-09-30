"""Writing operational records safely."""

from __future__ import annotations

import traceback
import uuid
from typing import Any

from app.core.logging import REDACTED, redact_text, request_id_var
from app.models import ErrorLog
from app.models.enums import Severity
from app.repositories.base import BaseRepository

_SENSITIVE_KEYS = ("password", "secret", "token", "api_key", "apikey", "authorization", "cookie")
_MAX_TEXT = 10_000


def _scrub(value: Any, key: str = "") -> Any:
    if any(word in key.lower() for word in _SENSITIVE_KEYS):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)[:_MAX_TEXT]
    if isinstance(value, dict):
        return {str(k): _scrub(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_scrub(v) for v in value]
    return value


class ErrorLogRepository(BaseRepository[ErrorLog]):
    model = ErrorLog

    async def record(
        self,
        exc: BaseException,
        *,
        component: str,
        severity: Severity = Severity.ERROR,
        context: dict[str, Any] | None = None,
        collection_job_id: uuid.UUID | None = None,
        content_id: uuid.UUID | None = None,
    ) -> ErrorLog:
        """Store an error with credentials removed from message, trace and context."""
        stack = "".join(traceback.format_exception(exc))
        entry = ErrorLog(
            severity=severity,
            component=component,
            error_type=type(exc).__name__,
            message=_scrub(str(exc)) or type(exc).__name__,
            stack_trace=_scrub(stack),
            context=_scrub(context or {}),
            request_id=request_id_var.get(),
            collection_job_id=collection_job_id,
            content_id=content_id,
        )
        return await self.add(entry)
