"""Shared permission constants for AnywhereInput.

This module defines the canonical list of permissions and their mappings
to avoid duplication across the codebase.
"""

from typing import List, Dict

# Canonical permission names
PERMISSIONS: List[str] = [
    "move",
    "click",
    "scroll",
    "keyboard",
    "screen_toggle",
    "ping",
]

# Map WebSocket message types to required permissions
MESSAGE_PERMISSION_MAP: Dict[str, str | None] = {
    "move": "move",
    "click": "click",
    "double_click": "click",
    "mouse_down": "click",
    "mouse_up": "click",
    "scroll": "scroll",
    "key": "keyboard",
    "type": "keyboard",
    "hotkey": "keyboard",
    "screen_toggle": "screen_toggle",
    "screen_restart": "screen_toggle",
    "ping": None,  # ping bypasses permission checks
}

# Default permissions granted to new tokens
DEFAULT_PERMISSIONS = tuple(PERMISSIONS)


def get_permission_for_message(msg_type: str) -> str | None:
    """Get the required permission for a WebSocket message type.

    Args:
        msg_type: The WebSocket message type (e.g., "move", "click", "key").

    Returns:
        The permission name required, or None if no permission needed.
    """
    return MESSAGE_PERMISSION_MAP.get(msg_type)


def get_default_permissions() -> list[str]:
    """Return a fresh copy of the default permission list."""
    return list(DEFAULT_PERMISSIONS)
