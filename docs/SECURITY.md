# Security Guide

## Token Authentication
- A new 32-character random token is generated on every server start
- Tokens are stored in `trusted_tokens.json` (included in `.gitignore` by default)
- Press **`n`** then Enter to rotate tokens instantly - all existing connections are dropped and a new token is generated
- Each connected WebSocket tracks its authenticated token; permissions are enforced on **every** guarded input message (`move`, `click`, `scroll`, `key`, `hotkey`, `screen_toggle`, etc.)

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
- **Single active token per session** - token rotation invalidates all previous tokens
- No built-in rate limiting on incoming connections
- No audit logging of who connected and what commands were sent

## Hardening Recommendations

### For untrusted networks (e.g., public WiFi)
1. Always use a tunnel provider with HTTPS (Cloudflare, Zrok2, Pinggy)
2. Don't use the local-only mode on shared networks

### For exposed servers (reverse proxy setup)
Add nginx/traefik in front of the server for:
- **OAuth2 authentication** - require login before reaching AnywhereInput
- **mTLS client certificates** - only authenticated clients can connect
- **Rate limiting** - prevent brute-force on the token endpoint

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
- Use strong tunnel URLs
- Monitor `trusted_tokens.json` for unexpected tokens
