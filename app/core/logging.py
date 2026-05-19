"""
app/core/logging.py
────────────────────
Cấu hình structured JSON logging dùng structlog.

Mọi log đều có dạng:
  {"level": "info", "timestamp": "...", "trace_id": "abc123", "event": "...", ...}

Cách dùng:
  from app.core.logging import get_logger
  log = get_logger(__name__)
  log.info("event.name", key=value)
"""

import logging
import structlog
from app.core.config import settings


def setup_logging() -> None:
    is_dev = settings.environment.lower() in ["dev", "development", "local"]

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if is_dev:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = "") -> structlog.BoundLogger:
    return structlog.get_logger(name)