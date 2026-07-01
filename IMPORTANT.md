# AnywhereInput Important Quick Notes

Read this before first run.

- Use setup script once, then run script.
- Keep the session token private.
- If token leaks, restart server to rotate token.
- Expected disconnects: only on server stop or explicit client disconnect.
- Monitor selector should list all detected displays plus Auto mode.
- For full details, see docs/IMPORTANT.md.

## Fast validation

python3 -m pytest tests/
python3 -m build --sdist --wheel
python3 -m twine check dist/*
