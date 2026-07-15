"""Info/Guide panel - app documentation and quick reference."""

from PyQt6.QtWidgets import (
    QTextEdit,
)
from PyQt6.QtGui import QFont


class InfoPanel(QTextEdit):
    """Scrollable info panel with app documentation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Sans", 10))
        self.setStyleSheet("""
            QTextEdit {
                background: #1a1f2e;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        self._build_content()

    def _build_content(self):
        sections = [
            (
                "What is AnywhereInput?",
                (
                    "AnywhereInput lets you control your PC from any browser - "
                    "phone, tablet, or another computer. No app install needed on the client side.\n\n"
                    "The server runs on your PC and streams a live JPEG screen capture over WebSocket. "
                    "Your mouse, keyboard, and scroll commands are sent back to the server in real time."
                ),
            ),
            (
                "How it works",
                (
                    "1. Start the server on your PC via this admin app\n"
                    "2. Pick a tunnel provider (Cloudflare, Tailscale, Pinggy, Zrok2) or use local mode\n"
                    "3. Open the URL on any device's browser\n"
                    "4. Paste the access token and connect\n"
                    "5. Control your PC from the browser - move cursor, click, type, scroll"
                ),
            ),
            (
                "Server Controls",
                (
                    "• ▶ Start Server - launches the AnywhereInput server with selected tunnel\n"
                    "• ■ Stop Server - shuts down the server gracefully\n"
                    "• Settings panel - configure port, FPS, JPEG quality, stream scale, and tunnel provider"
                ),
            ),
            (
                "Token Management",
                (
                    "Each token controls what a connected device can do.\n\n"
                    "• Per-token permissions: move, click, scroll, keyboard, screen_toggle, ping\n"
                    "• IP allowlists restrict which networks can use the token (CIDR or single host)\n"
                    "• Create, edit, revoke tokens, or remove multiple at once\n"
                    "• Auto-generated 32-char token on each server start - press 'n' in terminal to rotate"
                ),
            ),
            (
                "Connection Request Flow",
                (
                    "Clients can request access instead of having a pre-made token.\n\n"
                    "• Requests appear under 'Pending Connection Requests'\n"
                    "• Approve → generates a token for that client\n"
                    "• Decline → rejects the request\n"
                    "• Approved requests show their token (copy button)"
                ),
            ),
            (
                "Clients Monitoring",
                (
                    "• Connected WebSocket clients with their IPs\n"
                    "• Engine health: Healthy, Degraded, Recovering, Offline\n"
                    "• Screen capture status per session"
                ),
            ),
            (
                "Tunnel Providers",
                (
                    "• Cloudflare - free, auto-download cloudflared, random URLs each session\n"
                    "• Tailscale - P2P on your tailnet, requires account\n"
                    "• Pinggy.io - SSH-based, works behind strict firewalls, 60min timeout\n"
                    "• Zrok2 - open-source, zero-trust, free tier (5GB/day)\n"
                    "• Local - same WiFi/LAN only, no tunnel"
                ),
            ),
            (
                "Keyboard Shortcuts",
                (
                    "In the admin app:\n• 'n' + Enter - rotate server token\n"
                    "On connected clients:\n• ⌨️ keyboard button → type/send text\n"
                    "• Shortcuts tab: Copy, Cut, Paste, Undo, Redo, Save, Find, etc.\n"
                    "• System tab: Ctrl+Alt+Del, Alt+Tab, Task Manager, Screenshot\n"
                    "• Platform extras auto-detect server OS (Win/macOS/Linux)\n\n"
                    "Also supports virtual keyboard input for mobile devices."
                ),
            ),
            (
                "Security Notes",
                (
                    "⚠️ Designed for personal/trusted use. Not hardened for production.\n\n"
                    "• Auto-generated tokens rotate on server restart\n"
                    "• All data stays on your machine - zero cloud storage\n"
                    "• Tunnel providers provide HTTPS/WSS encryption\n"
                    "• Local mode has NO encryption - use a reverse proxy if exposed\n"
                    "• For production: add nginx/Traefik with OAuth or mTLS"
                ),
            ),
            (
                "Troubleshooting",
                (
                    "• Server won't start → check port is free, Python 3.9+ installed\n"
                    "• Tunnel URL not showing → check internet, try another provider\n"
                    "• Can't connect → verify both devices online, check firewall port\n"
                    "• Mouse lag → try local network; reduce FPS or quality\n"
                    "• Black screen → check server logs, ensure pyautogui/mss installed\n"
                    "• Zrok2 'not enabled' → run zrok2 enable <TOKEN> first"
                ),
            ),
        ]

        content = "<html><head><style>"
        content += "h3 { color: #94a3b8; margin-top: 16px; font-size: 15px; }"
        content += "p, li { color: #cbd5e1; line-height: 1.6; font-size: 12px; white-space: pre-wrap; }"
        content += ".divider { color: #334155; font-size: 18px; text-align: center; padding: 4px 0; margin: 8px 0; }"
        content += "</style></head><body>"
        content += '<h2 style="color:#e2e8f0; font-size:16px; margin-top:8px;">AnywhereInput - Admin Guide</h2>'

        for title, body in sections:
            content += (
                f'<div class="divider">── · ──</div><h3>{title}</h3><p>{body}</p>'
            )

        # Hotkey reference table
        hotkeys = [
            ("Ctrl + C", "Copy"),
            ("Ctrl + X", "Cut"),
            ("Ctrl + V", "Paste"),
            ("Ctrl + A", "Select All"),
            ("Ctrl + Z", "Undo"),
            ("Ctrl + Y", "Redo"),
            ("Ctrl + S", "Save"),
            ("Ctrl + F", "Find"),
            ("Ctrl + W", "Close Tab/Window"),
            ("Ctrl + N", "New"),
            ("Ctrl + R", "Refresh"),
            ("Ctrl + T", "New Tab"),
            ("", ""),
            ("Alt + Tab", "Switch Windows"),
            ("Alt + F4", "Close Window"),
            ("Ctrl + Shift + Esc", "Task Manager"),
            ("Ctrl + Alt + Del", "Windows Security Screen"),
            ("Print Screen", "Screenshot"),
            ("Ctrl + Esc", "Start Menu"),
            ("", ""),
            ("Win + D", "Show Desktop"),
            ("Win + E", "File Explorer"),
            ("Win + R", "Run Dialog"),
            ("Win + L", "Lock Screen"),
            ("Win + Tab", "Task View"),
            ("", ""),
            ("⌘ + C / V / Z", "Copy / Paste / Undo (macOS)"),
            ("⌘ + Tab", "Switch Apps (macOS)"),
            ("⌘ + Q", "Quit App (macOS)"),
            ("⌥ + ⌘ + ⎋", "Force Quit (macOS)"),
            ("⌘ + Space", "Spotlight (macOS)"),
        ]
        content += '<div class="divider">── · ──</div><h3>⌨️ Hotkey Reference</h3>'

        th_style = "padding:6px 10px;text-align:left;color:#94a3b8;font-size:12px;border-bottom:2px solid #4a5568;"
        td_code_style = "background:#1e293b;padding:2px 6px;border-radius:3px;font-family:monospace;"

        hdr = (
            f'<tr style="background:#2d3748;">'
            f'<th style="{th_style}">Shortcut</th>'
            f'<th style="{th_style}">Use Case</th></tr>'
        )
        content += hdr

        for sc, desc in hotkeys:
            if not sc and not desc:
                content += '<tr><td colspan="2" style="padding:2px 0;border-bottom:1px solid #4a5568;"></td></tr>'
            else:
                tr = (
                    '<tr style="border-bottom:1px solid #2d3748;">'
                    f'<td style="{td_code_style}"><code>{sc}</code></td>'
                    f'<td style="padding:5px 10px;font-size:12px;color:#cbd5e1;">{desc}</td></tr>'
                )
                content += tr
        content += "</table>"

        content += "</body></html>"
        self.setHtml(content)
        self.verticalScrollBar().setValue(0)
