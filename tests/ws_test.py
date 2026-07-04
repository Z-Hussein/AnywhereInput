"""Self-contained WebSocket integration test.

This test starts the server in-process on an ephemeral port so it does not
depend on a manually launched server.
"""

import asyncio
from contextlib import suppress

import aiohttp

from anywhereinput.server import AnywhereInputServer


async def _wait_until_listening(port: int, timeout: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(f"http://127.0.0.1:{port}/api/screen") as resp:
                    if resp.status == 200:
                        return
            except aiohttp.ClientError:
                pass
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Server did not start on port {port}")
            await asyncio.sleep(0.05)


async def _cleanup_server(server: AnywhereInputServer, task: asyncio.Task) -> None:
    server._running = False
    server.mouse_worker.stop()

    if server._capture_task:
        server._capture_task.cancel()
        with suppress(asyncio.CancelledError):
            await server._capture_task

    server.tunnel_manager.stop()

    async with server.clients_lock:
        for ws in list(server.clients):
            with suppress(Exception):
                await ws.close()
        server.clients.clear()

    if server.runner:
        with suppress(Exception):
            await server.runner.cleanup()

    server.screen.close()

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def test_ws_rejects_invalid_token(free_tcp_port):
    async def _run() -> None:
        server = AnywhereInputServer(host="127.0.0.1", port=free_tcp_port)
        task = asyncio.create_task(server.start(tunnel_provider=None))

        try:
            await _wait_until_listening(free_tcp_port)
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"ws://127.0.0.1:{free_tcp_port}/ws") as ws:
                    await ws.send_json({"type": "auth", "token": "invalid-token"})
                    response = await ws.receive_json(timeout=2)
                    assert response["type"] == "error"
                    assert "Invalid token" in response["message"]
        finally:
            await _cleanup_server(server, task)

    asyncio.run(_run())
