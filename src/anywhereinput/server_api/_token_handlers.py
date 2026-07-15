"""Token management API endpoints (admin-facing token CRUD)."""

from aiohttp import web


class TokenAPI:
    """Token CRUD endpoints - registered as aiohttp routes."""

    def __init__(self, server):
        self._srv = server

    async def list_tokens(self, request):
        """Return all active tokens (masked values)."""
        token_list = []
        for tok, info in self._srv.token_manager.tokens.items():
            token_list.append(
                {
                    "token": tok[:12] + "...",
                    "full_token": tok,
                    "name": info.get("name", "auto-generated"),
                    "created": info.get("created", ""),
                    "permissions": info.get("permissions", []),
                }
            )
        return web.json_response({"tokens": token_list})

    async def create_token(self, request):
        """Create a new token - merges with existing store."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = body.get("name", body.get("label", "manual") or "manual")
        permissions = body.get(
            "permissions", self._srv.token_manager.DEFAULT_PERMISSIONS()
        )
        new_token = self._srv.token_manager.generate_token(name=name, length=32)
        # Overwrite default permissions with custom ones
        if new_token in self._srv.token_manager.tokens:
            self._srv.token_manager.tokens[new_token]["permissions"] = permissions
            self._srv.token_manager._save_tokens()
        return web.json_response(
            {"token": new_token, "name": name, "permissions": permissions},
            status=201,
        )

    async def revoke_token(self, request):
        """Revoke a token by its full value."""
        full_token = request.match_info.get("token_id", "")
        ok = self._srv.token_manager.revoke(full_token)
        if not ok:
            return web.json_response({"error": "Token not found"}, status=404)
        return web.json_response({"ok": True})

    async def update_token(self, request):
        """Update token name or permissions."""
        full_token = request.match_info.get("token_id", "")
        if full_token not in self._srv.token_manager.tokens:
            return web.json_response({"error": "Token not found"}, status=404)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        token_info = self._srv.token_manager.tokens[full_token]
        if "name" in body:
            token_info["name"] = body["name"]
        if "permissions" in body:
            token_info["permissions"] = body["permissions"]
        self._srv.token_manager._save_tokens()
        return web.json_response({"ok": True, "token": token_info})

    def register_routes(self, router):
        """Register token routes on the aiohttp router."""
        router.add_get("/api/tokens", self.list_tokens)
        router.add_post("/api/tokens", self.create_token)
        router.add_delete("/api/tokens/{token_id}", self.revoke_token)
        router.add_patch("/api/tokens/{token_id}", self.update_token)
        # Client management
        router.add_get("/api/clients", self.list_clients)
        router.add_post("/api/clients/{client_id}/kick", self.kick_client)
        # Blocked IPs management
        router.add_get("/api/tokens/{token_id}/blocked-ips", self.list_blocked_ips)
        router.add_delete("/api/tokens/{token_id}/blocked-ips/{ip}", self.unblock_ip)

    async def list_clients(self, request):
        """Return currently connected WebSocket clients."""
        client_list = []
        async with self._srv.clients_lock:
            for ws in self._srv.clients:
                token = self._srv._client_tokens.get(ws)
                meta = self._srv._client_meta.get(ws)
                client_id = meta.get("client_id", "") if meta else ""
                # Validate client_id is a proper string, not a WebSocket object repr
                if not isinstance(client_id, str) or "WebSocketResponse" in client_id or "<" in client_id or ">" in client_id:
                    client_id = ""
                client_list.append(
                    {
                        "id": client_id,
                        "ip": meta.get("ip", "unknown") if meta else "unknown",
                        "token": token[:12] + "..." if token else "unknown",
                        "full_token": token if token else "",
                        "connected": not ws.closed,
                    }
                )
        return web.json_response({"clients": client_list})

    async def kick_client(self, request):
        """Kick a client and add their IP to the token's block list."""
        client_id = request.match_info.get("client_id", "")

        # Validate client_id - reject WebSocket object repr strings
        if not isinstance(client_id, str) or "WebSocketResponse" in client_id or "<" in client_id or ">" in client_id:
            return web.json_response({"error": "Invalid client ID"}, status=400)

        # Find the client by ID
        ws_to_kick = None
        token_to_kick = None
        client_ip = None

        async with self._srv.clients_lock:
            for ws in self._srv.clients:
                meta = self._srv._client_meta.get(ws)
                if meta and meta.get("client_id") == client_id:
                    ws_to_kick = ws
                    token_to_kick = self._srv._client_tokens.get(ws)
                    if meta:
                        # Parse IP from stored format
                        ip_str = meta.get("ip", "")
                        if ip_str.startswith("["):
                            # Bracketed IPv6 with port: [::1]:8080 -> extract ::1
                            bracket_end = ip_str.find("]")
                            client_ip = ip_str[1:bracket_end] if bracket_end > 0 else ""
                        elif ip_str.count(":") >= 2 or "%" in ip_str:
                            # Bare IPv6 (no brackets): 2003:abc::1 or 2003:abc::1%eth0
                            client_ip = ip_str.split("%")[0]  # strip zone index if present
                        else:
                            # IPv4 with optional port: 192.168.1.1:8080 -> extract 192.168.1.1
                            client_ip = ip_str.split(":")[0] if ":" in ip_str else ip_str
                    break

        if ws_to_kick is None:
            return web.json_response({"error": "Client not found"}, status=404)

        if token_to_kick is None or token_to_kick not in self._srv.token_manager.tokens:
            # Close without adding to block list
            await ws_to_kick.close()
            return web.json_response(
                {"ok": True, "message": "Client disconnected (no token)"}
            )

        # Add client IP to token's block list
        if client_ip:
            token_data = self._srv.token_manager.tokens[token_to_kick]
            blocked_ips = token_data.get("blocked_ips", [])
            if client_ip not in blocked_ips:
                blocked_ips.append(client_ip)
                token_data["blocked_ips"] = blocked_ips
                self._srv.token_manager._save_tokens()

        # Close the WebSocket connection
        try:
            await ws_to_kick.close()
        except Exception:
            pass

        return web.json_response(
            {
                "ok": True,
                "message": f"Client kicked, IP {client_ip} added to block list",
            }
        )

    async def list_blocked_ips(self, request):
        """Return blocked IPs for a token."""
        token_id = request.match_info.get("token_id", "")
        if token_id not in self._srv.token_manager.tokens:
            return web.json_response({"error": "Token not found"}, status=404)
        token_data = self._srv.token_manager.tokens[token_id]
        blocked_ips = token_data.get("blocked_ips", [])
        return web.json_response({"blocked_ips": blocked_ips})

    async def unblock_ip(self, request):
        """Remove an IP from a token's block list."""
        token_id = request.match_info.get("token_id", "")
        ip = request.match_info.get("ip", "")
        if token_id not in self._srv.token_manager.tokens:
            return web.json_response({"error": "Token not found"}, status=404)
        token_data = self._srv.token_manager.tokens[token_id]
        blocked_ips = token_data.get("blocked_ips", [])
        if ip not in blocked_ips:
            return web.json_response({"error": "IP not in block list"}, status=404)
        blocked_ips.remove(ip)
        token_data["blocked_ips"] = blocked_ips
        self._srv.token_manager._save_tokens()
        return web.json_response({"ok": True, "message": f"IP {ip} unblocked"})
