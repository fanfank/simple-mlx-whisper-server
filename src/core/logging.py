"""Structured logging configuration for the MLX Whisper Server."""

import sys
import uuid
from typing import Any, Dict, List

import structlog
from structlog.typing import EventDict


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add unique request ID to log entries."""
    if "request_id" not in event_dict:
        event_dict["request_id"] = str(uuid.uuid4())
    return event_dict


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID for request tracing."""
    if "correlation_id" not in event_dict:
        event_dict["correlation_id"] = str(uuid.uuid4())
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO 8601 timestamp to log entries."""
    from datetime import datetime

    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def filter_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Filter sensitive data from log entries."""
    sensitive_keys = {"audio_content", "api_key", "password", "token"}

    # Create a new dict without sensitive keys
    filtered = {}
    for key, value in event_dict.items():
        if key.lower() not in sensitive_keys:
            filtered[key] = value

    return filtered


def setup_logging(level: str = "INFO", format_type: str = "json") -> None:
    """Configure structured logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Log format (json or text)
    """
    # Configure processors as a list
    processors: List[Any] = [
        structlog.stdlib.filter_by_level,
        add_request_id,
        add_correlation_id,
        add_timestamp,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        filter_sensitive_data,
    ]

    if format_type == "json":
        processors.extend([
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer()
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    import logging

    # Set level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
        force=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)
