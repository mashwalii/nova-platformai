"""HTTP middleware (pure ASGI, so they also work with streaming responses).

Order, from outermost to innermost (configured in ``app.main``)::

    SecurityHeadersMiddleware  -> adds security headers to every response
    CORSMiddleware             -> browser cross-origin rules
    RequestContextMiddleware   -> request ID, access log, catches unexpected errors
    BodySizeLimitMiddleware    -> rejects oversized request bodies
    FastAPI routes
"""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response
from app.core.logging import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")
_QUIET_PATHS = frozenset({"/health", "/ready"})
# Swagger UI loads its assets from a CDN, so the strict API CSP is skipped there.
_DOCS_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/redoc"})

access_logger = logging.getLogger("nova.access")
error_logger = logging.getLogger("nova.errors")


class RequestContextMiddleware:
    """Assigns a request ID, writes the access log, and converts crashes into 500s."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = (
            incoming if incoming and _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        )
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            error_logger.exception(
                "unhandled error", extra={"method": scope["method"], "path": scope["path"]}
            )
            if response_started:
                raise
            response = error_response(500, "internal_error", "An unexpected error occurred.")
            await response(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            level = logging.DEBUG if scope["path"] in _QUIET_PATHS else logging.INFO
            # Only the path is logged: query strings may contain personal data.
            access_logger.log(
                level,
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_var.reset(token)


class SecurityHeadersMiddleware:
    """Adds defensive HTTP headers to every response."""

    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_docs = scope["path"] in _DOCS_PATHS

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
                if not is_docs:
                    headers.setdefault(
                        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
                    )
                if self.hsts:
                    headers.setdefault(
                        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Rejects request bodies larger than ``max_bytes`` with HTTP 413.

    Bodies with a declared ``Content-Length`` are rejected before the app runs.
    Streamed bodies are counted while being read: once the limit is crossed the
    413 response is sent immediately, the app sees a client disconnect, and any
    response the app tries to send afterwards is discarded.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0
        response_started = False
        rejected = False

        async def limited_receive() -> Message:
            nonlocal received, rejected
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    rejected = True
                    if not response_started:
                        await self._reject(scope, receive, send)
                    return {"type": "http.disconnect"}
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if rejected:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, send_wrapper)
        except Exception:
            if not rejected:
                raise
            # The 413 was already sent; errors caused by the cut-off body are expected.

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = error_response(
            413,
            "payload_too_large",
            f"The request body must not exceed {self.max_bytes} bytes.",
        )
        await response(scope, receive, send)
