# syntax=docker/dockerfile:1
# NOVA AI backend image (used for both the API and, later, the background worker).
#
# Build:  docker build -t nova-backend backend/
# Run:    docker run --rm -p 8000:8000 -e APP_ENV=development nova-backend
#         (production requires DATABASE_URL and CORS_ALLOW_ORIGINS)

# Base image; override to use a registry mirror, e.g.
#   --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.12-slim
ARG PYTHON_IMAGE=python:3.12-slim

# ---- Build stage: install locked dependencies into a virtualenv -------------
FROM ${PYTHON_IMAGE} AS builder

RUN pip install --no-cache-dir "uv==0.8.17"
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- Runtime stage: small image, non-root user --------------------------------
FROM ${PYTHON_IMAGE} AS runtime

RUN groupadd --system --gid 10001 nova \
    && useradd --system --uid 10001 --gid nova --home-dir /srv --no-create-home nova

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    API_HOST=0.0.0.0 \
    PORT=8000

WORKDIR /srv
COPY --from=builder /opt/venv /opt/venv
COPY --chown=nova:nova alembic.ini ./
COPY --chown=nova:nova alembic ./alembic
COPY --chown=nova:nova app ./app

USER nova
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)" || exit 1

# Hosting platforms (e.g. Render) set $PORT; default 8000.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT} --no-access-log"]
