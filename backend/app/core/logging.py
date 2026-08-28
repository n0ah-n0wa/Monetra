"""Structured application logging."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import MutableMapping
from datetime import UTC, datetime
from typing import Any, Literal

from app.core.redaction import redact_mapping
from app.core.request_context import get_request_id
from app.core.telemetry import get_span_id, get_trace_id

SERVICE_NAME = "monetra-backend"
LogFormat = Literal["text", "json"]


class _ContextFilter(logging.Filter):
    """Inject correlation fields into every log record."""

    def __init__(self, *, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service"):
            record.service = self._service_name
        record.request_id = get_request_id() or "-"
        record.trace_id = get_trace_id() or "-"
        record.span_id = get_span_id() or "-"
        if not hasattr(record, "event"):
            record.event = "-"
        return True


class JsonLogFormatter(logging.Formatter):
    """CloudWatch-friendly JSON log lines on stdout."""

    def __init__(self, *, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", self._service_name),
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
            "event": getattr(record, "event", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "service",
                "request_id",
                "trace_id",
                "span_id",
                "event",
            }:
                continue
            if key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=True)


def configure_logging(
    *,
    level: str = "INFO",
    log_format: LogFormat = "text",
    service_name: str = SERVICE_NAME,
) -> None:
    """Configure application-wide structured logging."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter(service_name=service_name))
    if log_format == "json":
        handler.setFormatter(JsonLogFormatter(service_name=service_name))
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt=(
                    "%(asctime)s %(levelname)s service=%(service)s "
                    "request_id=%(request_id)s trace_id=%(trace_id)s "
                    "event=%(event)s logger=%(name)s %(message)s"
                ),
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            ),
        )
    root.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).handlers.clear()
        logging.getLogger(logger_name).propagate = True


class ServiceLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that injects stable service metadata."""

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[str, MutableMapping[str, Any]]:
        extra = dict(kwargs.get("extra") or {})
        service = SERVICE_NAME
        if self.extra:
            service = str(self.extra.get("service", service))
        extra.setdefault("service", service)
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> ServiceLoggerAdapter:
    return ServiceLoggerAdapter(
        logging.getLogger(name),
        {"service": SERVICE_NAME},
    )


def log_event(
    logger: logging.Logger | ServiceLoggerAdapter,
    event: str,
    *,
    level: int = logging.INFO,
    exc_info: BaseException | bool | None = None,
    **fields: Any,
) -> None:
    """Emit a structured application event with sensitive fields redacted."""
    safe_fields = redact_mapping(fields)
    extra = {"event": event, **safe_fields}
    logger.log(
        level,
        "event=%s",
        event,
        extra=extra,
        exc_info=exc_info,
    )
