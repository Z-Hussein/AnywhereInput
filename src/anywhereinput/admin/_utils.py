"""Shared helpers for the admin package."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths - locate the project root relative to this package
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent  # .../anywhereinput/admin/
_ANYWHEREINPUT_DIR = _THIS_DIR.parent  # .../anywhereinput/
_PROJECT_ROOT = _ANYWHEREINPUT_DIR.parent.parent
