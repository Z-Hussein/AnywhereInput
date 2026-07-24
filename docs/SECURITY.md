# Security Guide

## Token Authentication
- A new 32-character random token is generated on every server start
- All previous tokens are **cleared on startup** - zero-trust, fresh session every restart
- Press **`n`** to rotate tokens instantly - a new token is generated (pressing `Enter` is not required)
- New tokens can also be triggered at runtime by setting the environment variable `AITOKEN_ROTATE=1` on any node running the server
- Multiple tokens can coexist simultaneously - rotation does **not** revoke existing tokens

## Per-Token Permissions
Each token carries a list of allowed input types:
- `move` - mouse movement
- `click` - click / double-click / mouse_down / mouse_up
- `scroll` - scroll wheel
- `keyboard` - key press, text typing, hotkeys
- `screen_toggle` - enable/disable screen capture
- `ping` - health check pings (always allowed)

Create restricted tokens via:
- Admin app (`anywhereinput --app`) → Tokens tab → + New Token
- API: `POST /api/tokens` with `{ "name": "...", "permissions": ["move", "click"] }`

## IP Allowlist
Tokens can be restricted to specific IPs or CIDR ranges via the admin app or token API. Empty allowlist = allow all.

## Rate Limiting
Built-in per-IP rate limiting protects against brute-force attacks:

| Endpoint | Limit | Window | Burst |
|----------|-------|--------|-------|
| WebSocket auth (`/ws`) | 10 requests | 1 second | +5 (effective: 15) |
| Token creation (`/api/tokens`) | 5 requests | 10 seconds | - |
| General API (`/api/*`) | 30 requests | 1 second | +10 (effective: 40) |

- **Localhost excluded** - `127.0.0.1`, `::1`, and `localhost` are never rate-limited
- **Static files excluded** - `/favicon.ico` and `/static/` paths bypass rate limiting
- Returns HTTP 429 with `Retry-After` header when exceeded

## Audit Logging
All security-relevant events are logged to `logs/audit.log` (JSON-lines, rotating 5MB × 10 files):

| Event | What's Logged |
|-------|---------------|
| `token.created` | Token prefix, name, permissions, allowed_ips, creator IP |
| `token.revoked` | Token prefix, revoker IP, reason |
| `token.rotated` | Old/new token prefix, rotator IP |
| `token.validated` | Token prefix, client IP, success/failure |
| `client.connected` | Client IP, token prefix, client ID |
| `client.disconnected` | Client IP, token prefix, reason |
| `client.kicked` | Target IP, kicker IP, client ID |
| `ip.blocked` | Blocked IP, blocker IP |
| `ip.unblocked` | Unblocked IP, unblocker IP |
| `connection.requested` | Client name, client IP, request ID |
| `connection.approved` | Request ID, approver IP, token prefix |
| `connection.declined` | Request ID, decliner IP |
| `admin.config_changed` | Setting name, old/new value, admin IP |

View audit logs:
```bash
tail -f logs/audit.log | python3 -m json.tool
```

## HTTPS / WSS Encryption
All tunnel providers provide HTTPS automatically:
| Tunnel | Encryption |
|--------|-----------|
| Cloudflare | HTTPS via `trycloudflare.com` domain |
| Pinggy.io | HTTPS via SSH-tunneled endpoint |
| Zrok2 | Zero-trust architecture with per-session encryption |
| Tailscale | Peer-to-peer encrypted - no public URL, stays on your tailnet |

**Local-only mode (option 6) has NO encryption.** If you need to use it, wrap it behind a reverse proxy or SSH tunnel.

## Known Limitations
- **Rate limiting is per-IP** - shared NAT/VPN IPs share the same bucket
- Audit log rotates at 5MB × 10 files (50MB max)

## Hardening Recommendations

### For untrusted networks (e.g., public WiFi)
1. Always use a tunnel provider with HTTPS (Cloudflare, Zrok2, Pinggy)
2. Don't use the local-only mode on shared networks

### For exposed servers (reverse proxy setup)
Add nginx/traefik in front of the server for:
- **OAuth2 authentication** - require login before reaching AnywhereInput
- **mTLS client certificates** - only authenticated clients can connect
- **Additional rate limiting** - for stricter limits beyond built-in defaults

Example nginx snippet:
```nginx
location / {
    proxy_pass http://127.0.0.1:8008;
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    client_max_body_size 0;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Best Practices
- Rotate the token periodically (press `n` + Enter)
- Use per-token permissions to restrict what restricted devices can do
- Use IP allowlists to limit which networks each token can connect from
- Never expose port 8008 directly to the internet without authentication
- Monitor `logs/audit.log` for suspicious activity
- Check blocked IPs via admin app token editor
