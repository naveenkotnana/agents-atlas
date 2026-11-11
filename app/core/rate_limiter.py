"""app/core/rate_limiter.py
Production-grade In-Memory Sliding Window Rate Limiter.

Uses an atomic sliding-window log to track request timestamps per client.
Guarantees accurate rate limiting across window boundaries without the
2x burst vulnerability of fixed-window counters.
"""
import time
import asyncio
from collections import defaultdict, deque
from fastapi import Request, status
from app.core.exceptions import AtlasBaseException
from app.core.logging import logger


class SlidingWindowRateLimiter:
    """
    Sliding-window rate limiter maintaining a deque of Unix timestamps per key.
    Thread-safe and async-compatible using asyncio.Lock.
    """

    def __init__(self, requests_per_minute: int = 60, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._history: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """
        Evaluates whether a request for `key` is permitted.
        Returns: (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        async with self._lock:
            timestamps = self._history[key]

            # Evict timestamps older than the active sliding window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            current_count = len(timestamps)

            if current_count < self.requests_per_minute:
                timestamps.append(now)
                remaining = self.requests_per_minute - (current_count + 1)
                return True, remaining, 0
            else:
                # Calculate when the oldest request in the window expires
                oldest_timestamp = timestamps[0]
                retry_after = max(1, int(oldest_timestamp + self.window_seconds - now))
                return False, 0, retry_after

    async def check_rate_limit(self, request: Request, cost: int = 1):
        """
        FastAPI dependency helper. Extracts client key (IP or user_id)
        and enforces the rate limit.
        """
        # Prefer authenticated user ID if available, otherwise fallback to client IP
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        key = f"rate:{user_id or client_ip}:{request.url.path}"

        allowed, remaining, retry_after = await self.is_allowed(key)

        # Attach rate limit telemetry to request.state for header injection
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = self.requests_per_minute

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for [{key}]. Retry-After: {retry_after}s"
            )
            raise AtlasBaseException(
                message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                error_code="RATE_LIMIT_EXCEEDED",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )


# Default global instances for different endpoint tiers
standard_rate_limiter = SlidingWindowRateLimiter(requests_per_minute=60, window_seconds=60)
heavy_query_rate_limiter = SlidingWindowRateLimiter(requests_per_minute=10, window_seconds=60)
