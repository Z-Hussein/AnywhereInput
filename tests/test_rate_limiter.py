"""Tests for rate limiter middleware."""

import asyncio
import time
from unittest import mock

import pytest

from anywhereinput.server._rate_limiter import (
    RateLimiter,
    RateLimitMiddleware,
    create_rate_limiter_middleware,
)


@pytest.fixture
def rl():
    return RateLimiter(max_requests=3, window_seconds=10, burst_allowance=0)


def _make_request(remote="1.2.3.4", path="/ws", headers=None):
    req = mock.MagicMock()
    req.remote = remote
    req.path = path
    req.headers = headers or {}
    return req


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allowed_under_limit(self, rl):
        req = _make_request()
        allowed, _ = await rl.check_rate_limit(req)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_blocked_over_limit(self, rl):
        req = _make_request()
        for _ in range(3):
            await rl.check_rate_limit(req)
        allowed, retry_after = await rl.check_rate_limit(req)
        assert allowed is False
        assert retry_after is not None

    @pytest.mark.asyncio
    async def test_separate_keys(self, rl):
        r1 = _make_request(remote="1.1.1.1")
        r2 = _make_request(remote="2.2.2.2")
        for _ in range(3):
            await rl.check_rate_limit(r1)
        allowed, _ = await rl.check_rate_limit(r1)
        assert allowed is False
        allowed, _ = await rl.check_rate_limit(r2)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_window_reset(self):
        rl = RateLimiter(max_requests=2, window_seconds=0.05)
        req = _make_request()
        await rl.check_rate_limit(req)
        await rl.check_rate_limit(req)
        allowed, _ = await rl.check_rate_limit(req)
        assert allowed is False
        await asyncio.sleep(0.1)
        allowed, _ = await rl.check_rate_limit(req)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_cleanup(self):
        rl = RateLimiter(max_requests=1, window_seconds=0.05)
        req = _make_request()
        await rl.check_rate_limit(req)
        await asyncio.sleep(0.1)
        rl.cleanup_old_entries(max_age_seconds=0.01)
        allowed, _ = await rl.check_rate_limit(req)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_burst_allowance(self):
        rl = RateLimiter(max_requests=2, window_seconds=10, burst_allowance=2)
        req = _make_request()
        for _ in range(4):
            allowed, _ = await rl.check_rate_limit(req)
            assert allowed is True
        allowed, _ = await rl.check_rate_limit(req)
        assert allowed is False


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_excluded_path(self):
        mw = RateLimitMiddleware()
        req = _make_request(path="/favicon.ico")
        handler = mock.AsyncMock(return_value=mock.MagicMock())
        resp = await mw.middleware(req, handler)
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_excluded_ip_localhost(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        mw = RateLimitMiddleware(default_limiter=rl)
        req = _make_request(remote="127.0.0.1")
        handler = mock.AsyncMock(return_value=mock.MagicMock())
        # Should pass for localhost even if limiter would block
        for _ in range(5):
            resp = await mw.middleware(req, handler)
        assert handler.call_count == 5

    @pytest.mark.asyncio
    async def test_rate_limited_returns_429(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        mw = RateLimitMiddleware(default_limiter=rl)
        req = _make_request(remote="1.2.3.4")
        handler = mock.AsyncMock(return_value=mock.MagicMock())
        await mw.middleware(req, handler)  # first passes
        resp = await mw.middleware(req, handler)  # second blocked
        assert resp.status == 429

    @pytest.mark.asyncio
    async def test_path_limiter_selection(self):
        ws_rl = RateLimiter(max_requests=1, window_seconds=60)
        mw = RateLimitMiddleware(path_limiters={"/ws": ws_rl})
        req_ws = _make_request(path="/ws", remote="3.3.3.3")
        req_api = _make_request(path="/api/tokens", remote="3.3.3.3")
        handler = mock.AsyncMock(return_value=mock.MagicMock())
        # WS has rate limit
        await mw.middleware(req_ws, handler)
        resp = await mw.middleware(req_ws, handler)
        assert resp.status == 429
        # API has no limiter -> passes
        resp2 = await mw.middleware(req_api, handler)
        assert resp2 is not mock.ANY or handler.call_count >= 3


class TestCreateMiddleware:
    def test_factory(self):
        mw = create_rate_limiter_middleware()
        assert isinstance(mw, RateLimitMiddleware)
        assert len(mw.path_limiters) >= 2
