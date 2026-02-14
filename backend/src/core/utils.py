"""Utility functions and helpers."""

import asyncio
import time
import uuid
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from .exceptions import OMNIError
from .logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def timing_decorator(
    func: Callable[..., T]
) -> Callable[..., T]:
    """Decorator to measure and log function execution time.
    
    Args:
        func: Function to wrap.
        
    Returns:
        Wrapped function that logs execution time.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "Function executed",
                function=func.__name__,
                duration_ms=round(elapsed_ms, 2),
            )
    
    return wrapper


def async_timing_decorator(
    func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T]]:
    """Async version of timing decorator.
    
    Args:
        func: Async function to wrap.
        
    Returns:
        Wrapped function that logs execution time.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "Async function executed",
                function=func.__name__,
                duration_ms=round(elapsed_ms, 2),
            )
    
    return wrapper


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Text to truncate.
        max_length: Maximum allowed length.
        suffix: Suffix to append if truncated.
        
    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    
    return text[: max_length - len(suffix)] + suffix


def safe_json_dumps(data: Any, max_length: int | None = None) -> str:
    """Safely convert data to JSON string.
    
    Args:
        data: Data to convert.
        max_length: Optional maximum length to truncate to.
        
    Returns:
        JSON string representation.
    """
    import json
    
    try:
        result = json.dumps(data, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        result = f'{{"error": "Failed to serialize: {e}"}}'
    
    if max_length and len(result) > max_length:
        result = result[:max_length] + "... [truncated]"
    
    return result


def estimate_token_count(text: str, chars_per_token: int = 4) -> int:
    """Estimate token count for text (character-based heuristic).
    
    This is a simple approximation. For more accurate counts,
    use a proper tokenizer.
    
    Args:
        text: Text to estimate.
        chars_per_token: Average characters per token.
        
    Returns:
        Estimated token count.
    """
    return len(text) // chars_per_token


def format_duration_ms(duration_ms: float) -> str:
    """Format duration in milliseconds to human-readable string.
    
    Args:
        duration_ms: Duration in milliseconds.
        
    Returns:
        Formatted duration string.
    """
    if duration_ms < 1000:
        return f"{duration_ms:.0f}ms"
    elif duration_ms < 60000:
        return f"{duration_ms / 1000:.2f}s"
    else:
        minutes = int(duration_ms // 60000)
        seconds = (duration_ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize a string for safe logging/display.
    
    Args:
        value: String to sanitize.
        max_length: Maximum length.
        
    Returns:
        Sanitized string.
    """
    # Remove control characters
    sanitized = "".join(char for char in value if char.isprintable() or char.isspace())
    return truncate_text(sanitized, max_length)


def validate_uuid(value: str) -> bool:
    """Validate if string is a valid UUID.
    
    Args:
        value: String to validate.
        
    Returns:
        True if valid UUID, False otherwise.
    """
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.
    
    Args:
        base: Base dictionary.
        override: Dictionary with override values.
        
    Returns:
        Merged dictionary.
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    error_message: str | None = None
) -> T:
    """Execute coroutine with timeout.
    
    Args:
        coro: Coroutine to execute.
        timeout_seconds: Timeout in seconds.
        error_message: Optional custom error message.
        
    Returns:
        Coroutine result.
        
    Raises:
        OMNIError: If timeout occurs.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        msg = error_message or f"Operation timed out after {timeout_seconds}s"
        raise OMNIError(msg, error_code="TIMEOUT_ERROR")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exceptions: Tuple of exception types to catch.
        
    Returns:
        Decorator function.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            "Retrying after error",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        time.sleep(delay)
            
            raise last_exception or OMNIError("Max retries exceeded")
        
        return wrapper
    
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Async version of retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exceptions: Tuple of exception types to catch.
        
    Returns:
        Decorator function.
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            "Retrying after error",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)
            
            raise last_exception or OMNIError("Max retries exceeded")
        
        return wrapper
    
    return decorator