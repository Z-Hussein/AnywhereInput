# Usage Guide

## Touchpad Controls

| Action | How |
|--------|-----|
| Move cursor | Drag on touchpad area |
| Left click | Tap touchpad (if enabled) or Left Click button |
| Right click | Long-press touchpad (600ms) or Right Click button |
| Double click | Double Click button |
| Scroll | Two-finger drag on touchpad, or Scroll buttons |
| Center mouse | Center button |

## Screen Overlay
Tap anywhere on the live screen stream to move the cursor to that location and click. (Only functional on the main display for now.)

## Keyboard
- Tap **Keyboard** button to open text input
- Type text and tap **Send**
- Use **Enter**, **Esc**, **Tab**, **Backspace** buttons
- Use hotkey buttons for common shortcuts

## Settings Panel
Tap the gear icon to access:
- **Screen Capture**: Toggle live stream
- **Mouse Sensitivity**: 0.3x to 3.0x
- **Show FPS Counter**: Display stream performance
- **Tap to Click**: Enable/disable tap-to-click
- **Long Press = Right Click**: Enable/disable long-press gesture

## Token Permissions (Admin App)
When managing tokens via `anywhereinput --app` or the token API, you can restrict what each token is allowed to do:

| Permission | Allows |
|-----------|--------|
| `move` | Mouse movement (relative + absolute) |
| `click` | Click, double-click, mouse_down, mouse_up |
| `scroll` | Scroll wheel input |
| `keyboard` | Key press, text typing, hotkeys |
| `screen_toggle` | Enable/disable screen capture stream |
| `ping` | Health check pings (always allowed) |

### IP Allowlist
In the admin app's token editor, set an IP allowlist to restrict which network addresses can use a token:
- Leave empty = allow all IPs
- Single host: `192.x.x.x`
- CIDR range: `192.x.x.x/24`
