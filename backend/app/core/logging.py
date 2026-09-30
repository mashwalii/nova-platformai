"""Logging setup.

* ``json`` format (default outside development): one JSON object per line,
  ready for log collectors.
* ``console`` format (default in development): readable single lines.

Every record carries the current request ID, and a redaction filter scrubs
credentials from messages and structured fields so secrets never reach logs.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import LogFormat, Settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

REDACTED = "***"

# Attributes present on every LogRecord; anything else was passed via `extra=`.
_STANDARD_RECORD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
    | {"message", "asctime", "request_id", "taskName", "color_message"}
)
# uvicorn calls its main logger "uvicorn.error" even for normal messages.
_LOGGER_DISPLAY_NAMES = {"uvicorn.error": "uvicorn"}
_SENSITIVE_KEY = re.compile(
    r"pass(word)?|secret|token|api[_-]?key|authorization|cookie|credential|private[_-]?key",
    re.IGNORECASE,
)
# user:password@ inside any URL (e.g. postgresql://user:pw@host/db)
_URL_CREDENTIALS = re.compile(r"(?P<prefix>[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s:/@]+:)[^\s@/]+@")
# "Bearer <token>" values
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*")

_HANDLER_MARKER = "_nova_handler"


def redact_text(text: str) -> str:
    text = _URL_CREDENTIALS.sub(rf"\g<prefix>{REDACTED}@", text)
    return _BEARER.sub(rf"\1{REDACTED}", text)


def _redact_value(key: str, value: Any) -> Any:
    if _SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    return value


class RedactingFilter(logging.Filter):
    """Removes credentials from log messages and `extra` fields."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact_value(str(k), v) for k, v in record.args.items()}
            else:
                record.args = tuple(
                    redact_text(a) if isinstance(a, str) else a for a in record.args
                )
        for key in list(vars(record)):
            if key not in _STANDARD_RECORD_ATTRS:
                setattr(record, key, _redact_value(key, getattr(record, key)))
        return True


class RequestIdFilter(logging.Filter):
    """Adds the current request ID (or None) to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {k: v for k, v in vars(record).items() if k not in _STANDARD_RECORD_ATTRS}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": _LOGGER_DISPLAY_NAMES.get(record.name, record.name),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S")
        request_id = getattr(record, "request_id", None)
        rid = f" [{request_id[:8]}]" if request_id else ""
        extras = " ".join(f"{k}={v}" for k, v in _extra_fields(record).items())
        name = _LOGGER_DISPLAY_NAMES.get(record.name, record.name)
        line = f"{timestamp} {record.levelname:<7} {name}{rid}: {record.getMessage()}"
        if extras:
            line = f"{line}  {extras}"
        if record.exc_info:
            line = f"{line}\n{redact_text(self.formatException(record.exc_info))}"
        return line


def configure_logging(settings: Settings) -> None:
    """Install NOVA's handler on the root logger. Safe to call more than once."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, _HANDLER_MARKER, True)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(RedactingFilter())
    handler.setFormatter(
        JsonFormatter() if settings.log_format == LogFormat.JSON else ConsoleFormatter()
    )
    root.addHandler(handler)
    root.setLevel(settings.log_level.value)

    # Route uvicorn's own logs through our handler; we write our own access log.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    # The auto-reloader reports every file change at INFO; only warnings matter.
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    # SQL echo is controlled by DATABASE_ECHO, not by the global level.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
