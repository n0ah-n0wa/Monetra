"""Structured logging configuration."""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any


class _ServiceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service"):
            record.service = "monetra-backend"
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ServiceFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt=(
                "%(asctime)s %(levelname)s service=%(service)s "
                "logger=%(name)s %(message)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).handlers.clear()
        logging.getLogger(logger_name).propagate = True


class ServiceLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that injects a stable service field."""

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[str, MutableMapping[str, Any]]:
        extra = dict(kwargs.get("extra") or {})
        service = "monetra-backend"
        if self.extra:
            service = str(self.extra.get("service", service))
        extra.setdefault("service", service)
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> ServiceLoggerAdapter:
    return ServiceLoggerAdapter(
        logging.getLogger(name),
        {"service": "monetra-backend"},
    )
