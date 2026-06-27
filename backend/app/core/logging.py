import logging
import sys
from pythonjsonlogger import jsonlogger
from functools import lru_cache
from app.core.config import get_settings


class ResearchJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter.
    Adds consistent fields to every log entry
    so log aggregators can parse them reliably.
    """

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Always present
        log_record["timestamp"] = record.asctime if hasattr(record, "asctime") else ""
        log_record["level"] = record.levelname
        log_record["module"] = record.module
        log_record["function"] = record.funcName

        # Optional trace field — set when research_id is available
        if "research_id" in message_dict:
            log_record["research_id"] = message_dict.pop("research_id")


def setup_logging() -> None:
    """
    Called once at application startup.
    Configures the root logger with JSON formatting.
    All named loggers inherit this configuration.
    """
    settings = get_settings()

    # Map log level string to logging constant
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # JSON handler — writes to stdout
    # In production, stdout is captured by the platform (Render, Docker)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = ResearchJsonFormatter(
        fmt="%(timestamp)s %(level)s %(module)s %(function)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # Remove default handlers
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@lru_cache
def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger for the calling module.

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("research created", extra={"research_id": str(research_id)})
    """
    return logging.getLogger(name)