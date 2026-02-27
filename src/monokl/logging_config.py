"""Logging configuration for Monokl.

Provides structured logging with console and file output using structlog.
Logs are written to both console (human-readable) and file (JSON format).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

import structlog

LOG_DIR = Path.home() / ".local" / "share" / "monokl" / "logs"
DEFAULT_LOG_LEVEL = "INFO"

# Sensitive field patterns to filter
SENSITIVE_PATTERNS = [
    r"token",
    r"password",
    r"secret",
    r"api[_-]?key",
    r"auth",
    r"credential",
    r"private[_-]?key",
    r"access[_-]?token",
    r"refresh[_-]?token",
    r"bearer",
]

# Compiled regex for case-insensitive matching
_SENSITIVE_REGEX = re.compile(
    r"|".join(SENSITIVE_PATTERNS),
    re.IGNORECASE,
)

# Mask for sensitive values
MASK = "***REDACTED***"


def ensure_log_dir() -> None:
    """Create log directory if it doesn't exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file_path() -> Path:
    """Get log file path with date suffix.

    Returns:
        Path to log file with naming: monokl_YYYY-MM-DD.log

    Example:
        path = get_log_file_path()
        # Returns: ~/.local/share/monokl/logs/monokl_2024-01-15.log
    """
    ensure_log_dir()
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"monokl_{date_str}.log"


def filter_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Filter sensitive data from log events.

    Masks values for keys that match sensitive patterns like
    'token', 'password', 'secret', etc.

    Args:
        logger: The logger instance
        method_name: The logging method being called
        event_dict: The event dictionary containing log data

    Returns:
        Modified event_dict with sensitive values masked
    """
    for key in event_dict:
        if isinstance(key, str) and _SENSITIVE_REGEX.search(key):
            if isinstance(event_dict[key], str) and len(event_dict[key]) > 0:
                event_dict[key] = MASK
    return event_dict


def configure_logging(debug: bool = False) -> None:
    """Configure structlog with console and file output.

    Sets up structured logging with:
    - Console output: human-readable with colors
    - File output: JSON format for analysis
    - Configurable log level via debug flag or LOG_LEVEL env var
    - Sensitive data filtering

    Args:
        debug: If True, set log level to DEBUG. Otherwise uses LOG_LEVEL
               env var or defaults to INFO.

    Example:
        # Configure with default INFO level
        configure_logging()

        # Configure with DEBUG level
        configure_logging(debug=True)

        # Configure with LOG_LEVEL env var
        import os
        os.environ["LOG_LEVEL"] = "WARNING"
        configure_logging()
    """
    # Determine log level
    if debug:
        log_level = "DEBUG"
    else:
        log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    # Ensure log directory exists
    ensure_log_dir()
    log_file = get_log_file_path()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level),
        handlers=[
            logging.FileHandler(log_file),
        ],
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            filter_sensitive_data,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if os.environ.get("LOG_FORMAT") == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name, typically __name__ from the calling module.
              If None, returns the root logger.

    Returns:
        Configured BoundLogger instance for structured logging.

    Example:
        logger = get_logger(__name__)
        logger.info("User action", user_id=123, action="login")
        logger.debug("Processing data", item_count=42)
        logger.error("Operation failed", error_code=500)
    """
    return structlog.get_logger(name)
