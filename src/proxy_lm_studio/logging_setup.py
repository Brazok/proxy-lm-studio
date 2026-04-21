"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from proxy_lm_studio.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure structlog with processors appropriate for the environment.

    Args:
        settings: Application settings used to determine renderer and log level.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    renderer: structlog.types.Processor
    if settings.env == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_request_context(method: str, path: str, client_ip: str) -> str:
    """Clear previous context and bind a new request_id for the current request.

    Args:
        method: HTTP method (GET, POST, …).
        path: Request path.
        client_ip: Client IP address.

    Returns:
        The generated request_id UUID string.
    """
    structlog.contextvars.clear_contextvars()
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=method,
        path=path,
        client_ip=client_ip,
    )
    return request_id
