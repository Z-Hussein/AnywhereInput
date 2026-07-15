"""TokenStore - local JSON persistence (pure Python, no Qt dependency)."""

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ._utils import _PROJECT_ROOT


class TokenStore:
    """Persisted token store backed by a JSON file - supports IP allowlist & permissions."""

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path) if path else _PROJECT_ROOT / "admin_tokens.json"
        self._data: Dict[str, dict] = {}
        self.load()

    # -- public API -----------------------------------------------------------

    def create(
        self,
        name: str = "manual",
        permissions: Optional[List[str]] = None,
        allowed_ips: Optional[List[str]] = None,
    ) -> str:
        token = secrets.token_urlsafe(32)
        self._data[token] = {
            "name": name,
            "created": datetime.now(timezone.utc).isoformat(),
            "permissions": permissions
            or [
                "move",
                "click",
                "scroll",
                "keyboard",
                "screen_toggle",
            ],
            "allowed_ips": allowed_ips or [],
        }
        self.save()
        return token

    def revoke(self, token: str) -> bool:
        if token in self._data:
            del self._data[token]
            self.save()
            return True
        return False

    def update(
        self,
        token: str,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        allowed_ips: Optional[List[str]] = None,
    ) -> bool:
        if token not in self._data:
            return False
        entry = self._data[token]
        if name is not None:
            entry["name"] = name
        if permissions is not None:
            entry["permissions"] = permissions
        if allowed_ips is not None:
            entry["allowed_ips"] = allowed_ips
        self.save()
        return True

    def list_all(self) -> List[dict]:
        out = []
        for tok, data in self._data.items():
            out.append(
                {
                    "token": tok[:12] + "...",  # short display
                    "full_token": tok,
                    "name": data["name"],
                    "created": data["created"],
                    "permissions": data.get("permissions", []),
                    "allowed_ips": data.get("allowed_ips", []),
                }
            )
        return out

    def get_all(self) -> Dict[str, dict]:
        return self._data.copy()

    # -- persistence ----------------------------------------------------------

    def load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)
