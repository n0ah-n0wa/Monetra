"""Structured application logging."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

from app.core.request_context import get_request_id

SERVICE_NAME = "monetra-backend"


class _ContextFilter(logging.Filter):
    """Inject service and request_id fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service"):
            record.service = SERVICE_NAME
        request_id = get_request_id()
        record.request_id = request_id or "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt=(
                "%(asctime)s %(levelname)s service=%(service)s "
                "request_id=%(request_id)s logger=%(name)s %(message)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
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
