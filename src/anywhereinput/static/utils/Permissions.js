/**
 * Shared permission constants for AnywhereInput client.
 * Mirrors the Python _permissions module to keep message types and
 * permission names in sync across the codebase.
 */

// Canonical permission names
export const PERMISSIONS = [
    "move",
    "click",
    "scroll",
    "keyboard",
    "screen_toggle",
    "ping",
];

// Map WebSocket message types to required permissions
export const MESSAGE_PERMISSION_MAP = {
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
    "ping": null,  // ping bypasses permission checks
};

// Default permissions granted to new tokens
export const DEFAULT_PERMISSIONS = [...PERMISSIONS];

/**
 * Get the required permission for a WebSocket message type.
 * @param {string} msgType - The WebSocket message type
 * @returns {string|null} The required permission name, or null if no permission needed
 */
export function getPermissionForMessage(msgType) {
    return MESSAGE_PERMISSION_MAP[msgType] ?? null;
}

/**
 * Get a fresh copy of the default permission list.
 * @returns {string[]} Fresh copy of default permissions
 */
export function getDefaultPermissions() {
    return [...DEFAULT_PERMISSIONS];
}
