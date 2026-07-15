"""Client serving the web UI."""

from pathlib import Path
from typing import Optional
from aiohttp import web


class ClientHandler:
    """Serves the HTML/JS/CSS client files with path traversal protection."""

    def __init__(self, static_dir: Optional[str] = None):
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
            with open(index_file, "r", encoding="utf-8") as f:
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
            ext = file_path.suffix.lower()
            mime_map = {
                ".html": "text/html",
                ".htm": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
            }
            content_type = mime_map.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                raw_data = f.read()

            # Serve text files with appropriate encoding, binary files as-is
            if ext in (".html", ".css", ".js", ".json"):
                data_text = raw_data.decode("utf-8")
                return web.Response(text=data_text, content_type=content_type)
            else:
                return web.Response(body=raw_data, content_type=content_type)
        return web.Response(text="Not found", status=404)

    async def favicon_handler(self, request: web.Request) -> web.Response:
        """Serve favicon.ico at root path (/favicon.ico)."""
        file_path = self._static_dir_resolved / "favicon.ico"
        if file_path.exists() and file_path.is_file():
            with open(file_path, "rb") as f:
                raw_data = f.read()
            return web.Response(body=raw_data, content_type="image/vnd.microsoft.icon")
        return web.Response(text="Not found", status=404)
