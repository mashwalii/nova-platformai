from __future__ import annotations

import json
import logging

from app.core.logging import (
    JsonFormatter,
    RedactingFilter,
    RequestIdFilter,
    configure_logging,
    redact_text,
    request_id_var,
)
from tests.conftest import make_settings


def _record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("nova.test", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_redact_text_hides_url_passwords_and_bearer_tokens() -> None:
    text = "connect postgresql://nova:hunter2@db:5432/x with Authorization: Bearer abc.def-123"
    redacted = redact_text(text)
    assert "hunter2" not in redacted
    assert "abc.def-123" not in redacted
    assert "postgresql://nova:***@db:5432/x" in redacted


def test_redacting_filter_masks_sensitive_extra_fields() -> None:
    record = _record(
        "login with postgresql://u:pw@h/db",
        password="pw",
        api_key="k",
        path="/v1/news",
    )
    RedactingFilter().filter(record)
    assert record.getMessage() == "login with postgresql://u:***@h/db"
    assert record.password == "***"  # type: ignore[attr-defined]
    assert record.api_key == "***"  # type: ignore[attr-defined]
    assert record.path == "/v1/news"  # type: ignore[attr-defined]


def test_json_formatter_includes_request_id_and_extras() -> None:
    token = request_id_var.set("req-123")
    try:
        record = _record("hello", status_code=200)
        RequestIdFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["status_code"] == 200
    assert "timestamp" in payload


def test_configure_logging_is_idempotent() -> None:
    settings = make_settings()
    configure_logging(settings)
    configure_logging(settings)
    ours = [h for h in logging.getLogger().handlers if getattr(h, "_nova_handler", False)]
    assert len(ours) == 1
    assert logging.getLogger("uvicorn.access").disabled is True
