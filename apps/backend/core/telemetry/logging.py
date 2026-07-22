import logging
from typing import Any

import structlog

from .context import get_correlation_id, get_span_id, get_trace_id

# Keys that should be redacted from logs
SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "credentials"}


def inject_context_ids(
    logger: logging.Logger, log_method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Injects context IDs into the structured log.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    trace_id = get_trace_id()
    if trace_id:
        event_dict["trace_id"] = trace_id

    span_id = get_span_id()
    if span_id:
        event_dict["span_id"] = span_id

    return event_dict


def redact_sensitive_data(
    logger: logging.Logger, log_method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Scrub sensitive keys from log payload.
    """

    def _scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: ("***REDACTED***" if k.lower() in SENSITIVE_KEYS else _scrub(v))
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_scrub(item) for item in obj]
        return obj

    return _scrub(event_dict)


def sample_debug_logs(
    logger: logging.Logger, log_method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Placeholder for sampling logic.
    Currently lets all logs through, but can be configured to drop debug logs based on a random roll.
    """
    # If log_method == "debug":
    #    if random.random() > 0.01:
    #        raise structlog.DropEvent
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog processors and renderer.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            inject_context_ids,
            redact_sensitive_data,
            sample_debug_logs,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(category: str) -> structlog.BoundLogger:
    """
    Retrieves a logger bound with a specific category.
    """
    logger = structlog.get_logger()
    return logger.bind(category=category)
