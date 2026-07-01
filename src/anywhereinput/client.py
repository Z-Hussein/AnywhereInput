"""Client serving the web UI."""

import os
from pathlib import Path
from aiohttp import web


class ClientHandler:
    """Serves the HTML/JS/CSS client files with path traversal protection."""

    def __init__(self, static_dir: str = None):
        if static_dir is None:
            self.static_dir = Path(__file__).parent / "static"
        else:
            self.static_dir = Path(static_dir)
        # Resolve once and cache
        self._static_dir_resolved = self.static_dir.resolve()

    async def index(self, request: web.Request) -> web.Response:
        """Serve the main client HTML."""
        index_file = self._static_dir_resolved / "client.html"
        if index_file.exists() and index_file.is_file():
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return web.Response(text=content, content_type="text/html")
        return web.Response(text="Client not found", status=404)

    async def static_file(self, request: web.Request) -> web.Response:
        """Serve static files (CSS, JS) with path traversal protection."""
        filename = request.match_info.get("filename", "")

        # Reject paths with directory traversal attempts
        if ".." in filename or filename.startswith("/") or "\\" in filename:
            return web.Response(text="Forbidden", status=403)

        file_path = (self._static_dir_resolved / filename).resolve()

        # Ensure the resolved path is still within the static directory
        try:
            file_path.relative_to(self._static_dir_resolved)
        except ValueError:
            return web.Response(text="Forbidden", status=403)

        if file_path.exists() and file_path.is_file():
            content_type = "text/css" if filename.endswith(".css") else "application/javascript"
            with open(file_path, 'r', encoding='utf-8') as f:
                return web.Response(text=f.read(), content_type=content_type)
        return web.Response(text="Not found", status=404)
