# Bug Reporting Guide

All known bugs have been fixed. If you find a new issue, please report it.

---

## 🐛 How to Report a Bug

### Before You Report

1. **Check existing issues** - Search [GitHub Issues](https://github.com/Z-Hussein/AnywhereInput/issues) to avoid duplicates.
2. **Update to latest** - Ensure you're on the newest version (`pip install -U anywhereinput`).
3. **Reproduce reliably** - Confirm the bug happens consistently, not intermittently.

### What to Include

| Field | Description |
|-------|-------------|
| **Summary** | One-line description of the problem |
| **Steps to Reproduce** | Numbered list of exact actions to trigger the bug |
| **Expected Behavior** | What should happen |
| **Actual Behavior** | What actually happens |
| **Environment** | OS, Python version, browser, tunnel provider |
| **Logs/Errors** | Relevant server/client logs, stack traces, screenshots |

### Bug Report Template

```markdown
## Summary
Brief description of the bug

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
- **Server OS:** Ubuntu 24.04 / Windows 11 / macOS 14
- **Python:** 3.11.9
- **Browser:** Chrome 126 / Safari 17 / Firefox 127
- **Tunnel:** Cloudflare / Tailscale / Pinggy / Zrok2 / Local
- **AnywhereInput version:** 1.2.7

## Logs
```
[Server] Frame delayed: 150.2ms (target 8.3ms)
[Client] Uncaught TypeError: Cannot read property 'getBoundingClientRect' of null
```

## Screenshots
(Optional) Attach screenshots or screen recordings

## Additional Context
Any other relevant information
```

---

## 📋 Common Debugging Info

When in doubt, include:

```bash
# Server version
anywhereinput --version

# Python environment
python -c "import anywhereinput; print(anywhereinput.__version__)"

# Check server logs (run with --tunnel local for clean output)
anywhereinput --tunnel local
```

---

## 🔗 Useful Links

- **Issues:** [github.com/Z-Hussein/AnywhereInput/issues](https://github.com/Z-Hussein/AnywhereInput/issues)
- **Discussions:** [github.com/Z-Hussein/AnywhereInput/discussions](https://github.com/Z-Hussein/AnywhereInput/discussions)
- **Roadmap:** [README.md#-roadmap](README.md#-roadmap)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

---

## ⚡ Quick Triage

| Symptom | Likely Cause | First Check |
|---------|--------------|-------------|
| Black screen | Display not available / MSS failure | Run with `--no-capture` to test |
| Mouse lag | High latency / low FPS | Lower `--quality`, increase `--fps` |
| Auth fails | Wrong token / IP blocked | Check server logs for "Invalid token" |
| Keyboard drops | Slow queue bug (fixed in 1.2.4) | Update to latest |
| Touch not working | Mobile browser restrictions | Use HTTPS/WSS via tunnel |

---

> **Tip:** The faster you can reproduce it, the faster it gets fixed. Minimal reproduction steps are gold.
