from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app import __version__
from app.main import create_app
from tests.conftest import make_settings


async def test_health_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "NOVA AI API", "version": __version__}


async def test_ready_without_database_is_unavailable(client: httpx.AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["database"]["status"] == "not_configured"


@pytest.fixture
def unreachable_db_app() -> FastAPI:
    # Nothing listens on port 1, so the connection is refused immediately.
    settings = make_settings(
        database_url="postgresql://nova:very-secret@127.0.0.1:1/nova_test",
        database_connect_timeout_seconds=1,
        health_check_timeout_seconds=2,
    )
    return create_app(settings)


async def test_ready_with_unreachable_database(unreachable_db_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=unreachable_db_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ready")
    await unreachable_db_app.state.database.dispose()

    assert response.status_code == 503
    database = response.json()["checks"]["database"]
    assert database["status"] == "error"
    assert database["detail"] == "database unreachable"
    assert "very-secret" not in response.text


async def test_v1_api_info(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1")
    assert response.status_code == 200
    assert response.json() == {
        "name": "NOVA AI API",
        "api_version": "v1",
        "version": __version__,
        "environment": "test",
        "docs_url": "/docs",
    }


async def test_docs_available_outside_production(client: httpx.AsyncClient) -> None:
    assert (await client.get("/docs")).status_code == 200
    schema = await client.get("/v1/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"]["version"] == __version__


async def test_docs_disabled_in_production() -> None:
    settings = make_settings(app_env="production", database_url="postgresql://u:p@127.0.0.1:1/nova")
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/v1/openapi.json")).status_code == 404
        info = await client.get("/v1")
    await app.state.database.dispose()
    assert info.json()["docs_url"] is None


async def test_lifespan_startup_and_shutdown() -> None:
    """Startup logs and shutdown closes the database pool without connecting."""
    app = create_app(make_settings(database_url="postgresql://u:p@127.0.0.1:1/nova"))
    async with app.router.lifespan_context(app):
        assert app.state.database is not None
    assert app.state.database.engine.pool.checkedout() == 0
