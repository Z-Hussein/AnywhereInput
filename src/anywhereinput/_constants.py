"""Shared constants for AnywhereInput.

Centralizes magic values used across the codebase to ensure consistency
and make configuration changes easier.
"""

# Network defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8008

# Tunnel provider choices
TUNNEL_CHOICES = ["cloudflare", "tailscale", "pinggy", "zrok2", "local"]

# Tunnel provider names (alias for CLI compatibility)
TUNNEL_PROVIDERS = TUNNEL_CHOICES

# Bind host constants
BIND_ALL = "0.0.0.0"
BIND_IPV6_ALL = "::"
LOCALHOST = "localhost"

# Backoff defaults
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_MAX_BACKOFF = 4.0
DEFAULT_RECOVERY_INTERVAL = 5.0  # seconds for ping check

# Screen capture defaults (also used by CLI and admin app)
DEFAULT_FPS = 120
DEFAULT_QUALITY = 40
DEFAULT_SCALE = 0.7

# Low-bandwidth preset (mobile data, slow connections)
LOW_BW_FPS = 15
LOW_BW_QUALITY = 60
LOW_BW_SCALE = 0.5
MIN_FPS = 1
MAX_FPS = 120
MIN_QUALITY = 1
MAX_QUALITY = 95
MIN_SCALE = 0.1
MAX_SCALE = 1.0

# Input defaults (mouse worker)
DEFAULT_SENSITIVITY = 1.5
DEFAULT_MOVE_INTERVAL = 0.002  # ~500Hz max move rate
MAX_MOVE_PER_BATCH = 800
MAX_MOVES_PER_SEC = 2000

# Queue sizes
INPUT_QUEUE_MAXSIZE = 100
SLOW_QUEUE_MAXSIZE = 50

# WebSocket
WS_HEARTBEAT_INTERVAL = 30.0  # aiohttp heartbeat
WS_PONG_TIMEOUT = 60.0  # custom pong timeout
WS_PING_INTERVAL = 30000  # client ping interval (ms)

# WebSocket close codes (RFC 6455 + custom 4xxx)
WS_CLOSE_NORMAL = 1000
WS_CLOSE_GOING_AWAY = 1001
WS_CLOSE_POLICY_VIOLATION = 1008
WS_CLOSE_SERVER_ERROR = 1011
WS_CLOSE_SERVER_RESTART = 1012
WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_ORIGIN_REJECTED = 4003
WS_CLOSE_KICKED = 4004

# Token
DEFAULT_TOKEN_LENGTH = 32
TOKEN_PREVIEW_LENGTH = 12

# Mouse
LONG_PRESS_DURATION = 600  # ms
BUTTON_CHECK_INTERVAL = 5.0  # seconds

# UI
STATUS_AUTO_HIDE_DELAY = 3000  # ms
COPY_FEEDBACK_DELAY = 1500  # ms
