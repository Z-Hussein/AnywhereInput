"""Rate limiting middleware for AnywhereInput server."""

import time
import asyncio
from typing import Optional, Dict, Tuple
from aiohttp import web
from anywhereinput.logging_config import get_logger

log = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter with per-IP tracking."""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: float = 1.0,
        burst_allowance: int = 0,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_allowance = burst_allowance
        self._buckets: Dict[str, Tuple[float, int]] = {}  # ip -> (window_start, count)
        self._lock = asyncio.Lock()

    def _get_key(self, request: web.Request) -> str:
        """Extract client IP for rate limiting."""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        peer = request.remote
        if isinstance(peer, str):
            return peer
        return getattr(peer, "host", "unknown") if peer else "unknown"

    async def check_rate_limit(
        self, request: web.Request
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.
        Returns: (allowed, retry_after_header_value_or_none)
        """
        key = self._get_key(request)
        now = time.monotonic()

        async with self._lock:
            window_start, count = self._buckets.get(key, (now, 0))

            if now - window_start >= self.window_seconds:
                window_start = now
                count = 0

            effective_limit = self.max_requests + self.burst_allowance
            if count >= effective_limit:
                retry_after = int(self.window_seconds - (now - window_start)) + 1
                return False, str(retry_after)

            self._buckets[key] = (window_start, count + 1)
            return True, None

    def cleanup_old_entries(self, max_age_seconds: float = 300.0) -> None:
        """Remove entries older than max_age_seconds."""
        now = time.monotonic()
        keys_to_remove = [
            key
            for key, (window_start, _) in self._buckets.items()
            if now - window_start > max_age_seconds
        ]
        for key in keys_to_remove:
            del self._buckets[key]


class RateLimitMiddleware:
    """Configurable rate limiting middleware for aiohttp."""

    def __init__(
        self,
        default_limiter: Optional[RateLimiter] = None,
        path_limiters: Optional[Dict[str, RateLimiter]] = None,
        excluded_prefixes: Optional[set] = None,
        excluded_ips: Optional[set] = None,
    ):
        self.default_limiter = default_limiter
        self.path_limiters = path_limiters or {}
        self.excluded_prefixes = excluded_prefixes or {"/favicon.ico", "/static/"}
        self.excluded_ips = excluded_ips or {"127.0.0.1", "::1", "localhost"}

    def _is_excluded(self, path: str) -> bool:
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True
        return False

    def _is_excluded_ip(self, request: web.Request) -> bool:
        key = self._get_key(request)
        return key in self.excluded_ips

    def _get_key(self, request: web.Request) -> str:
        """Extract client IP for rate limiting."""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        peer = request.remote
        if isinstance(peer, str):
            return peer
        return getattr(peer, "host", "unknown") if peer else "unknown"

    def _get_limiter_for_path(self, path: str) -> Optional[RateLimiter]:
        for pattern, limiter in self.path_limiters.items():
            if path.startswith(pattern):
                return limiter
        return self.default_limiter

    @web.middleware
    async def middleware(self, request: web.Request, handler):
        if self._is_excluded(request.path) or self._is_excluded_ip(request):
            return await handler(request)

        limiter = self._get_limiter_for_path(request.path)

        if limiter is None:
            return await handler(request)

        allowed, retry_after = await limiter.check_rate_limit(request)

        if not allowed:
            log.warning(
                "Rate limit exceeded for %s on %s",
                self._get_key(request),
                request.path,
            )
            response = web.Response(
                status=429,
                text="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": retry_after} if retry_after else {},
            )
            return response

        return await handler(request)


def create_rate_limiter_middleware() -> RateLimitMiddleware:
    """Create pre-configured rate limiter middleware for AnywhereInput."""

    # WebSocket auth: strict limit (10 attempts per second per IP, burst 5)
    ws_limiter = RateLimiter(max_requests=10, window_seconds=1.0, burst_allowance=5)

    # API endpoints: moderate limit (30 requests per second per IP, burst 10)
    api_limiter = RateLimiter(max_requests=30, window_seconds=1.0, burst_allowance=10)

    # Token creation: stricter (5 requests per 10 seconds per IP)
    token_create_limiter = RateLimiter(max_requests=5, window_seconds=10.0)

    return RateLimitMiddleware(
        default_limiter=None,  # No default limit
        path_limiters={
            "/ws": ws_limiter,
            "/api/tokens": token_create_limiter,
            "/api/": api_limiter,
            "/api/requests": api_limiter,
        },
        excluded_prefixes={"/favicon.ico", "/static/"},
    )
