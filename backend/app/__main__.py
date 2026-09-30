"""Start the API server: ``uv run python -m app``.

Host and port come from API_HOST / API_PORT. In development the server
restarts automatically when code changes.
"""

from __future__ import annotations

import uvicorn

from app.core.config import Environment, get_settings
from app.core.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    reload = settings.app_env == Environment.DEVELOPMENT
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=reload,
        reload_dirs=["app"] if reload else None,
        log_config=None,  # logging is configured by the app itself
        access_log=False,  # the app writes its own access log
    )


if __name__ == "__main__":
    main()
