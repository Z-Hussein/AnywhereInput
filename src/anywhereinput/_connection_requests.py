"""Shared global state for pending connection requests."""

import asyncio

_connection_requests: dict = {}
_connection_requests_lock = asyncio.Lock()
