# Bug Reporting Guide

If you find a bug, here's how to report it so it actually gets fixed.

## Before reporting

- Check [existing issues](https://github.com/Z-Hussein/anywhereinput/issues) to avoid duplicates
- Update to the latest version: `pip install -U anywhereinput`
- Try to reproduce consistently - intermittent bugs are harder to track down

## What to include

```markdown
## Summary
One-line description of the problem

## Steps to Reproduce
1. Start server with `anywhereinput --tunnel cloudflare`
2. Connect from mobile browser
3. Tap screen stream twice quickly
4. Observe behavior

## Expected Behavior
First tap moves cursor, second tap clicks

## Actual Behavior
First tap clicks immediately

## Environment
- Server OS: Ubuntu 24.04 / Windows 11 / macOS 14
- Python: 3.11.9
- Browser: Chrome 126 / Safari 17 / Firefox 127
- Tunnel: Cloudflare / Tailscale / Pinggy / Zrok2 / Local
- AnywhereInput version: 1.3.1

## Logs
```
[Server] Frame delayed: 150.2ms (target 8.3ms)
[Client] Uncaught TypeError: Cannot read property 'getBoundingClientRect' of null
```

## Screenshots
(Optional but helpful)

## Additional Context
Anything else that might be relevant
```

Minimal reproduction steps are the most helpful thing you can provide. If you can boil it down to "run this, see this" in 3 steps instead of a 20-step setup, the bug gets fixed faster.

## Quick self-checks

| Symptom | Check first |
|---------|-------------|
| Black screen | Run with `--no-capture` to test if it's capture-related |
| Mouse lag | Lower quality, increase FPS, check tunnel latency |
| Auth fails | Wrong token or IP blocked - check server logs for "Invalid token" |
| Keyboard drops | Fixed in 1.2.4 - update to latest |

## Useful commands

```bash
anywhereinput --version              # server version
python -c "import anywhereinput; print(anywhereinput.__version__)"  # installed version
anywhereinput --tunnel local          # clean output, no tunnel noise
```

Issues: https://github.com/Z-Hussein/anywhereinput/issues
Discussions: https://github.com/Z-Hussein/anywhereinput/discussions
