"""Logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structlog and standard library logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: If True, output JSON logs; otherwise, output colored console logs.
    """
    # Configure structlog processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_logs:
        # JSON output for production
        structlog.configure(
            processors=shared_processors + [structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Pretty console output for development
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Redirect standard library logging through structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Optional logger name (usually __name__).
        
    Returns:
        A BoundLogger instance.
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding structured context to logs.
    
    Example:
        with LogContext(request_id="123", user_id="456"):
            logger.info("Processing request")
            # Logs will include request_id and user_id
    """
    
    def __init__(self, **context: Any) -> None:
        """Initialize with context key-value pairs.
        
        Args:
            **context: Key-value pairs to add to log context.
        """
        self.context = context
        self.token = None
    
    def __enter__(self) -> "LogContext":
        """Enter the context, adding values to structlog context."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context, unbinding the values."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_event(
    event: str,
    level: str = "info",
    **kwargs: Any
) -> None:
    """Log a structured event.
    
    Args:
        event: Event description.
        level: Log level (debug, info, warning, error, critical).
        **kwargs: Additional context fields.
    """
    logger = get_logger()
    method = getattr(logger, level.lower(), logger.info)
    method(event, **kwargs)


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """Log an HTTP request.
    
    Args:
        method: HTTP method.
        path: Request path.
        status_code: HTTP status code.
        duration_ms: Request duration in milliseconds.
        **kwargs: Additional context fields.
    """
    logger = get_logger()
    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        **kwargs
    )


def log_agent_action(
    agent_id: str,
    action: str,
    success: bool,
    duration_ms: float | None = None,
    **kwargs: Any
) -> None:
    """Log an agent action.
    
    Args:
        agent_id: Agent identifier.
        action: Action description.
        success: Whether the action succeeded.
        duration_ms: Action duration in milliseconds.
        **kwargs: Additional context fields.
    """
    logger = get_logger()
    level = "info" if success else "warning"
    method = getattr(logger, level)
    
    log_data = {
        "agent_id": agent_id,
        "action": action,
        "success": success,
    }
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    log_data.update(kwargs)
    
    method("agent_action", **log_data)


def log_tool_call(
    tool_id: str,
    success: bool,
    duration_ms: float | None = None,
    error: str | None = None,
    **kwargs: Any
) -> None:
    """Log a tool execution.
    
    Args:
        tool_id: Tool identifier.
        success: Whether the execution succeeded.
        duration_ms: Execution duration in milliseconds.
        error: Error message if execution failed.
        **kwargs: Additional context fields.
    """
    logger = get_logger()
    level = "info" if success else "warning"
    method = getattr(logger, level)
    
    log_data = {
        "tool_id": tool_id,
        "success": success,
    }
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    if error:
        log_data["error"] = error
    log_data.update(kwargs)
    
    method("tool_call", **log_data)