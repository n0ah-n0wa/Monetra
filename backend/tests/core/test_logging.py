"""Structured logging tests."""

import json
import logging

from app.core.logging import JsonLogFormatter, configure_logging, log_event


def test_json_formatter_emits_structured_fields() -> None:
    formatter = JsonLogFormatter(service_name="test-service")
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event=%s",
        args=("startup",),
        exc_info=None,
    )
    record.service = "test-service"
    record.request_id = "req-1"
    record.trace_id = "trace-1"
    record.span_id = "span-1"
    record.event = "startup"
    record.app_env = "test"

    payload = json.loads(formatter.format(record))
    assert payload["level"] == "INFO"
    assert payload["service"] == "test-service"
    assert payload["request_id"] == "req-1"
    assert payload["trace_id"] == "trace-1"
    assert payload["event"] == "startup"
    assert payload["app_env"] == "test"


def test_log_event_redacts_sensitive_fields(caplog) -> None:
    configure_logging(level="INFO", log_format="text", service_name="test-service")
    logging.getLogger().addHandler(caplog.handler)
    logger = logging.getLogger("test.observability")
    with caplog.at_level(logging.INFO):
        log_event(
            logger,
            "auth.login_failed",
            email="user@example.com",
            password="super-secret",
        )

    assert caplog.records
    record = caplog.records[-1]
    assert record.event == "auth.login_failed"
    assert record.email == "user@example.com"
    assert record.password == "[REDACTED]"
