# NOVA AI — Backend

Python + FastAPI backend for NOVA AI. See [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for the overall design and [`../IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md) for the roadmap.

> **Status: Phase 2 — foundation.** Health checks, configuration, logging, error handling, CORS, database connection layer, migrations, and tests. No product features (news, research, …) yet.

---

## Quick start

Requirements: **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (it installs the right Python version automatically).

```sh
cd backend
uv sync                      # install dependencies (first time, and after pulling changes)
uv run python -m app         # start the API on http://127.0.0.1:8000
```

Then open:

| URL | What you see |
| --- | --- |
| http://127.0.0.1:8000/health | `{"status":"ok",...}` — the server is running |
| http://127.0.0.1:8000/ready | database status (503 until a database is configured) |
| http://127.0.0.1:8000/v1 | API version information |
| http://127.0.0.1:8000/docs | interactive API documentation |

Stop the server with **Ctrl + C**.

No configuration is needed to start. To change settings, copy the template and edit your copy:

```sh
cp .env.example .env
```

---

## Commands

| Command | Purpose |
| --- | --- |
| `uv run python -m app` | Run the API (auto-reloads on code changes in development) |
| `uv run pytest` | Run the tests |
| `uv run pytest --cov` | Tests with a coverage report |
| `uv run ruff check .` | Lint (find mistakes) |
| `uv run ruff format .` | Auto-format code |
| `uv run mypy` | Type-check |
| `uv run alembic upgrade head` | Apply database migrations |
| `uv run alembic current` | Show the database's migration version |
| `uv run alembic revision --autogenerate -m "describe change"` | Create a migration from model changes (review it before committing!) |
| `uv run python -m app.cli config` | Show effective configuration (secrets hidden) |
| `uv run python -m app.cli check-db` | Test the database connection |
| `uv run python -m app.cli openapi -o openapi.json` | Export the API schema |

---

## Connecting a database

The backend works without a database; `/ready` then reports `not_configured`. To connect PostgreSQL:

1. Get a connection string:
   - **Supabase:** Project → *Connect* (or *Project Settings → Database*) → copy the **URI**. Use the *direct* or *session pooler* connection. If you use the *transaction pooler* (port 6543), also set `DATABASE_USE_PGBOUNCER=true`.
   - **Local PostgreSQL:** `postgresql://USER:PASSWORD@localhost:5432/DATABASE`
2. Put it in `backend/.env`: `DATABASE_URL=postgresql://...` (this file is never committed).
3. Apply migrations and check:
   ```sh
   uv run alembic upgrade head
   uv run python -m app.cli check-db
   ```
4. Start the API; `/ready` should now return `"status": "ok"`.

All NOVA tables live in the PostgreSQL schema **`app`**, which is not exposed through Supabase's public data API.

---

## Running the database tests

Unit and API tests need nothing. Database tests (marked `db`) are **skipped** unless `TEST_DATABASE_URL` points to a **throwaway** PostgreSQL database whose name contains `test` — the tests delete and recreate the `app` schema in it.

```sh
TEST_DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/nova_test uv run pytest
```

GitHub Actions runs all tests (including database tests) on every change to `backend/`.

---

## Project structure

```
backend/
├── app/
│   ├── __main__.py          # `python -m app` → starts the server
│   ├── main.py              # create_app(): builds the FastAPI application
│   ├── cli.py               # management commands
│   ├── core/                # config, database, logging, errors, middleware
│   ├── api/
│   │   ├── deps.py          # shared dependencies (settings, DB session, services)
│   │   ├── health.py        # /health and /ready (unversioned probes)
│   │   └── v1/              # everything under /v1
│   │       ├── router.py    # registers all v1 endpoint modules
│   │       └── endpoints/   # one module per feature
│   ├── services/            # business logic
│   ├── repositories/        # database queries (data access layer)
│   ├── models/              # SQLAlchemy tables (schema "app")
│   └── schemas/             # Pydantic request/response shapes (the API contract)
├── alembic/                 # migrations (versions/ holds each change)
├── tests/                   # unit/, api/, integration/ (database)
├── Dockerfile               # production image
└── pyproject.toml / uv.lock # dependencies (locked)
```

### Layering rule

```
API route  →  service  →  repository  →  database
```

* **Routes** (`api/`) handle HTTP only: parse input, call a service, return a schema.
* **Services** (`services/`) hold business rules and own the unit of work (they `commit`).
* **Repositories** (`repositories/`) contain queries and never commit. Extend `BaseRepository` for CRUD helpers.
* **Errors:** raise `NotFoundError`, `ConflictError`, etc. from `app.core.errors`; they become consistent JSON errors automatically.

### Adding an endpoint (example: news)

1. `app/models/news.py` — table; import it in `app/models/__init__.py`.
2. `uv run alembic revision --autogenerate -m "add news"` → review the generated file.
3. `app/repositories/news.py` — queries (`class NewsRepository(BaseRepository[News])`).
4. `app/services/news.py` — business logic.
5. `app/schemas/news.py` — response shapes.
6. `app/api/v1/endpoints/news.py` — `router = APIRouter(prefix="/news", tags=["news"])`.
7. Register it in `app/api/v1/router.py`: `api_router.include_router(news.router)`.
8. Tests in `tests/`.

---

## Built-in protections

| Area | Behaviour |
| --- | --- |
| Secrets | `SecretStr` settings; passwords never appear in logs, `repr`, CLI output, or validation errors |
| Production safety | Refuses to start in staging/production without `DATABASE_URL` or with wildcard CORS; API docs off in production |
| Errors | One JSON format `{"error": {code, message, details, request_id}}`; no stack traces or internal messages sent to clients |
| Request IDs | Every response has `X-Request-ID`; the same ID appears in every log line for that request |
| Logging | JSON logs outside development; credentials and bearer tokens are redacted automatically; query strings are not logged |
| Headers | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, strict CSP; HSTS when deployed |
| CORS | Explicit allow-list; no cookies/credentials |
| Limits | Request bodies over 1 MB (configurable) are rejected with 413; database statement timeout |
| Database | Least exposure: tables in schema `app`; default access revoked from public/Supabase API roles |
| Container | Non-root user, no dev dependencies, built-in health check |
| CI | Lint, type-check, tests with PostgreSQL, migration check, dependency vulnerability audit, Docker build |

---

## Configuration reference

All variables are documented in [`.env.example`](.env.example). The most important:

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `development`, `test`, `staging`, `production` |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Where `python -m app` listens |
| `LOG_LEVEL` | `INFO` | |
| `LOG_FORMAT` | console in development, json elsewhere | |
| `CORS_ALLOW_ORIGINS` | localhost dev ports in development; none when deployed | comma-separated |
| `DATABASE_URL` | not set | **secret**; required in staging/production |
| `DATABASE_MIGRATION_URL` | falls back to `DATABASE_URL` | **secret**; direct connection for migrations |
| `DATABASE_USE_PGBOUNCER` | `false` | `true` for Supabase transaction pooler (port 6543) |

---

## Docker

```sh
docker build -t nova-backend backend
docker run --rm -p 8000:8000 -e APP_ENV=development nova-backend
```

The image defaults to `APP_ENV=production`, which requires `DATABASE_URL` and `CORS_ALLOW_ORIGINS`. It listens on `$PORT` (default 8000). If Docker Hub rate-limits you, build from a mirror: `--build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.12-slim`.
