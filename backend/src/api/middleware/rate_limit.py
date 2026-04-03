"""Rate limiting middleware."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter middleware.

    Tracks requests per IP address with configurable limits.
    For production, use Redis-based rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit

        # Simple in-memory tracking: {ip: [(timestamp, count)]}
        self._request_log: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._cleanup_interval = 3600  # Cleanup every hour
        self._last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self) -> None:
        """Clean up entries older than 1 hour."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - 3600
        for ip in list(self._request_log.keys()):
            self._request_log[ip] = [
                (ts, count) for ts, count in self._request_log[ip] if ts > cutoff
            ]
            if not self._request_log[ip]:
                del self._request_log[ip]

        self._last_cleanup = current_time

    def _check_rate_limit(self, client_ip: str) -> tuple[bool, str]:
        """Check if request is within rate limits."""
        current_time = time.time()
        minute_ago = current_time - 60
        hour_ago = current_time - 3600

        # Get recent requests
        recent = self._request_log[client_ip]

        # Count requests in last minute
        minute_count = sum(count for ts, count in recent if ts > minute_ago)

        # Count requests in last hour
        hour_count = sum(count for ts, count in recent if ts > hour_ago)

        # Check burst limit
        if minute_count >= self.burst_limit:
            return False, "Rate limit exceeded (burst). Please wait before making more requests."

        # Check per-minute limit
        if minute_count >= self.requests_per_minute:
            return (
                False,
                "Rate limit exceeded (per minute). Please wait before making more requests.",
            )

        # Check per-hour limit
        if hour_count >= self.requests_per_hour:
            return False, "Rate limit exceeded (per hour). Please wait before making more requests."

        return True, ""

    def _record_request(self, client_ip: str) -> None:
        """Record a request."""
        current_time = time.time()
        self._request_log[client_ip].append((current_time, 1))

        # Merge adjacent entries
        recent = self._request_log[client_ip]
        if len(recent) > 1:
            # Keep only last 100 entries
            self._request_log[client_ip] = recent[-100:]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc"]:
            return await call_next(request)

        # Skip if rate limiting disabled
        if self.requests_per_minute <= 0:
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Check rate limits
        allowed, message = self._check_rate_limit(client_ip)
        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate Limit Exceeded",
                    "message": message,
                },
            )

        # Record request
        self._record_request(client_ip)

        # Cleanup old entries periodically
        self._cleanup_old_entries()

        return await call_next(request)
