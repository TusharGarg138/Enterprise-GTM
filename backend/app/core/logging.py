"""
Centralized structured logging configuration.
Uses Python's standard logging with JSON-like formatting for production readability.
Never logs secrets, API keys, or sensitive personal data.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable to propagate request IDs across async calls
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_var.get() or ""


def set_request_id(request_id: Optional[str] = None) -> str:
    rid = request_id or str(uuid.uuid4())[:8]
    _request_id_var.set(rid)
    return rid


class RequestIdFilter(logging.Filter):
    """Inject request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def configure_logging(debug: bool = False) -> None:
    """Configure application-wide logging. Call once at startup."""
    level = logging.DEBUG if debug else logging.INFO

    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s"
    )
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Avoid duplicate handlers if called multiple times (e.g., in tests)
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Preferred over direct logging.getLogger() calls."""
    return logging.getLogger(name)
