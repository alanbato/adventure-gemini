"""Logging configuration for Adventure."""

import hashlib
import sys
from pathlib import Path
from typing import Any

import structlog


def hash_fingerprint_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Hash user fingerprints in log events for privacy."""
    if "fingerprint" in event_dict:
        fp = event_dict["fingerprint"]
        if fp and fp != "unknown":
            hashed = hashlib.sha256(fp.encode()).hexdigest()[:12]
            event_dict["fingerprint_hash"] = hashed
            del event_dict["fingerprint"]
    return event_dict


def _level_to_int(level: str) -> int:
    levels = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    return levels.get(level.upper(), 20)


def configure_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_logs: bool = False,
    hash_fingerprints: bool = True,
) -> None:
    """Configure structured logging for the application."""
    if log_file:
        output_stream = open(log_file, "a")
    else:
        output_stream = sys.stdout

    base_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(
            fmt="iso" if json_logs else "%Y-%m-%d %H:%M:%S"
        ),
    ]

    if hash_fingerprints:
        base_processors.append(hash_fingerprint_processor)

    if json_logs:
        processors = base_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = base_processors + [
            structlog.dev.ConsoleRenderer(colors=output_stream.isatty())
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(_level_to_int(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output_stream),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance for a module."""
    return structlog.get_logger(name)
