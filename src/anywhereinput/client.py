"""Client serving the web UI."""

import os
from pathlib import Path
from aiohttp import web


class ClientHandler:
    """Serves the HTML/JS/CSS client files."""

    def __init__(self, static_dir: str = None):
        if static_dir is None:
            # Default to package static directory
            self.static_dir = Path(__file__).parent / "static"
        else:
            self.static_dir = Path(static_dir)

    async def index(self, request: web.Request) -> web.Response:
        """Serve the main client HTML."""
        index_file = self.static_dir / "client.html"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return web.Response(text=content, content_type="text/html")
        return web.Response(text="Client not found", status=404)

    async def static_file(self, request: web.Request) -> web.Response:
        """Serve static files (CSS, JS)."""
        filename = request.match_info.get("filename", "")
        file_path = self.static_dir / filename

        if file_path.exists() and file_path.is_file():
            content_type = "text/css" if filename.endswith(".css") else "application/javascript"
            with open(file_path, 'r', encoding='utf-8') as f:
                return web.Response(text=f.read(), content_type=content_type)
        return web.Response(text="Not found", status=404)
