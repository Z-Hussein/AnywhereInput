"""Shared helpers for the admin package."""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths - locate the project root relative to this package
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent  # .../anywhereinput/admin/
_ANYWHEREINPUT_DIR = _THIS_DIR.parent  # .../anywhereinput/
_PROJECT_ROOT = _ANYWHEREINPUT_DIR.parent.parent

# ---------------------------------------------------------------------------
# First-run state
# ---------------------------------------------------------------------------
_STATE_FILE = _PROJECT_ROOT / ".admin_state.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def is_first_run() -> bool:
    return not _load_state().get("setup_completed", False)


def mark_setup_completed() -> None:
    state = _load_state()
    state["setup_completed"] = True
    _save_state(state)
