"""Error types and the handlers that turn them into consistent JSON responses.

Every error response has the same shape::

    {"error": {"code": "not_found", "message": "...", "details": null, "request_id": "..."}}

Internal details (stack traces, SQL, secrets) are never sent to clients; they
are logged server-side with the request ID so they can be looked up.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger("nova.errors")


class AppError(Exception):
    """Base class for expected, client-facing errors raised by services."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    message = "The request is invalid."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Authentication is required."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "The request conflicts with the current state of the resource."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "The service is temporarily unavailable."


_HTTP_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    429: "rate_limited",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id_var.get(),
        }
    }
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - narrowing for the type checker
    log = logger.error if exc.status_code >= 500 else logger.info
    log(
        "request failed",
        extra={"error_code": exc.code, "status_code": exc.status_code, "path": request.url.path},
    )
    return error_response(exc.status_code, exc.code, exc.message, details=exc.details)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    status = exc.status_code
    code = _HTTP_CODES.get(status, "http_error")
    if status == 404 and exc.detail == "Not Found":
        message = NotFoundError.message  # friendlier than the framework default
    elif isinstance(exc.detail, str) and exc.detail:
        message = exc.detail
    else:
        try:
            message = HTTPStatus(status).phrase
        except ValueError:
            message = "Error"
    return error_response(status, code, message, headers=dict(exc.headers or {}))


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    # Only location, message and type: raw input values are not echoed back
    # because they may contain personal data or secrets.
    details = [
        {
            "loc": list(err.get("loc", ())),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return error_response(
        422, "validation_error", "The request contains invalid data.", details=details
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach NOVA's error handlers.

    Unexpected exceptions (bugs) are handled by ``RequestContextMiddleware``,
    which logs them and returns a generic 500 response.
    """
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
