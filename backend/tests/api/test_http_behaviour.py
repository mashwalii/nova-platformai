"""Cross-cutting HTTP behaviour: request IDs, errors, CORS, security headers, limits."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.errors import ConflictError, NotFoundError
from app.core.middleware import REQUEST_ID_HEADER
from app.main import create_app
from tests.conftest import make_settings

ALLOWED_ORIGIN = "https://nova.example.com"


class Item(BaseModel):
    name: str
    quantity: int


@pytest.fixture
def app() -> FastAPI:
    """App with extra routes that exercise error paths."""
    application = create_app(
        make_settings(cors_allow_origins=ALLOWED_ORIGIN, max_request_body_bytes=1024)
    )

    @application.post("/_test/items")
    async def create_item(item: Item) -> Item:
        return item

    @application.get("/_test/missing")
    async def missing() -> None:
        raise NotFoundError("Article not found.", code="article_not_found")

    @application.get("/_test/conflict")
    async def conflict() -> None:
        raise ConflictError(details={"field": "slug"})

    @application.get("/_test/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal detail")

    @application.get("/_test/needs-db")
    async def needs_db(session: DbSession) -> dict[str, str]:
        return {"status": "unreachable in this test"}

    @application.post("/_test/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    return application


# --- Request IDs ------------------------------------------------------------------


async def test_request_id_generated(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers[REQUEST_ID_HEADER])


async def test_valid_incoming_request_id_is_kept(client: httpx.AsyncClient) -> None:
    response = await client.get("/health", headers={REQUEST_ID_HEADER: "abc-123.XYZ_9"})
    assert response.headers[REQUEST_ID_HEADER] == "abc-123.XYZ_9"


@pytest.mark.parametrize("bad", ["has spaces", "x" * 129, "<script>"])
async def test_invalid_incoming_request_id_is_replaced(client: httpx.AsyncClient, bad: str) -> None:
    response = await client.get("/health", headers={REQUEST_ID_HEADER: bad})
    assert response.headers[REQUEST_ID_HEADER] != bad
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers[REQUEST_ID_HEADER])


# --- Error format -----------------------------------------------------------------


def _assert_error(response: httpx.Response, status: int, code: str) -> dict[str, object]:
    assert response.status_code == status
    error: dict[str, object] = response.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert isinstance(error["message"], str) and error["message"]
    return error


async def test_unknown_route_returns_404_error(client: httpx.AsyncClient) -> None:
    _assert_error(await client.get("/does-not-exist"), 404, "not_found")


async def test_wrong_method_returns_405_error(client: httpx.AsyncClient) -> None:
    response = await client.delete("/health")
    _assert_error(response, 405, "method_not_allowed")
    assert "GET" in response.headers["allow"]


async def test_app_errors_map_to_status_and_code(client: httpx.AsyncClient) -> None:
    error = _assert_error(await client.get("/_test/missing"), 404, "article_not_found")
    assert error["message"] == "Article not found."
    error = _assert_error(await client.get("/_test/conflict"), 409, "conflict")
    assert error["details"] == {"field": "slug"}


async def test_validation_error_does_not_echo_input(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/_test/items", json={"name": "private-value-123", "quantity": "many"}
    )
    error = _assert_error(response, 422, "validation_error")
    assert error["details"] == [
        {
            "loc": ["body", "quantity"],
            "message": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
    assert "many" not in response.text and "private-value-123" not in response.text


async def test_unhandled_error_returns_generic_500(client: httpx.AsyncClient) -> None:
    response = await client.get("/_test/crash", headers={"Origin": ALLOWED_ORIGIN})
    error = _assert_error(response, 500, "internal_error")
    assert error["message"] == "An unexpected error occurred."
    assert "secret internal detail" not in response.text
    # The browser must be able to read the error, so CORS headers are still present.
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


async def test_database_dependency_without_database(client: httpx.AsyncClient) -> None:
    _assert_error(await client.get("/_test/needs-db"), 503, "database_not_configured")


# --- CORS -------------------------------------------------------------------------


async def test_cors_preflight_allowed_origin(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/v1",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers


async def test_cors_disallowed_origin(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1", headers={"Origin": "https://evil.example.org"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_cors_exposes_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1", headers={"Origin": ALLOWED_ORIGIN})
    assert REQUEST_ID_HEADER.lower() in response.headers["access-control-expose-headers"].lower()


# --- Security headers -------------------------------------------------------------


async def test_security_headers_present(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")
    assert "strict-transport-security" not in response.headers  # only when deployed


async def test_docs_page_not_blocked_by_csp(client: httpx.AsyncClient) -> None:
    response = await client.get("/docs")
    assert "content-security-policy" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_hsts_enabled_when_deployed() -> None:
    app = create_app(
        make_settings(app_env="staging", database_url="postgresql://u:p@127.0.0.1:1/nova")
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as client:
        response = await client.get("/health")
    await app.state.database.dispose()
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")


# --- Request size limit -----------------------------------------------------------


async def test_body_within_limit_accepted(client: httpx.AsyncClient) -> None:
    response = await client.post("/_test/echo", content=b"x" * 1000)
    assert response.json() == {"size": 1000}


async def test_declared_oversized_body_rejected(client: httpx.AsyncClient) -> None:
    _assert_error(await client.post("/_test/echo", content=b"x" * 2048), 413, "payload_too_large")


async def test_streamed_oversized_body_rejected(client: httpx.AsyncClient) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        for _ in range(8):
            yield b"x" * 512

    # A generator body has no Content-Length, so the limit is enforced while reading.
    response = await client.post("/_test/echo", content=chunks())
    _assert_error(response, 413, "payload_too_large")
