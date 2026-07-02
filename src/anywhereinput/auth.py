"""Token-based authentication manager."""

import secrets
import json
import os
from pathlib import Path
from typing import Dict, Optional, List


class TokenManager:
    """Manages secure token generation, validation, and rotation."""

    DEFAULT_PERMISSIONS = ["move", "click", "scroll", "keyboard", "screen_toggle", "ping"]

    def __init__(self, token_file: str = "trusted_tokens.json"):
        self.token_file = Path(token_file)
        self.tokens: Dict[str, dict] = {}
        self._load_tokens()

    def generate_token(self, name: str = "auto-generated", length: int = 32) -> str:
        """Generate a new secure random token."""
        token = secrets.token_urlsafe(length)
        self.tokens[token] = {
            "name": name,
            "created": self._timestamp(),
            "permissions": self.DEFAULT_PERMISSIONS.copy(),
        }
        self._save_tokens()
        return token

    def validate(self, token: str, permission: Optional[str] = None) -> bool:
        """Validate a token and optionally check a permission."""
        if token not in self.tokens:
            return False
        if permission and permission not in self.tokens[token].get("permissions", []):
            return False
        return True

    def rotate(self) -> str:
        """Invalidate all existing tokens and generate a new one."""
        self.tokens.clear()
        return self.generate_token(name="rotated")

    def revoke(self, token: str) -> bool:
        """Revoke a specific token."""
        if token in self.tokens:
            del self.tokens[token]
            self._save_tokens()
            return True
        return False

    def list_tokens(self) -> List[dict]:
        """List all active tokens (without revealing values)."""
        return [
            {"name": v["name"], "created": v["created"], "permissions": v["permissions"]}
            for v in self.tokens.values()
        ]

    def _load_tokens(self) -> None:
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    self.tokens = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.tokens = {}

    def _save_tokens(self) -> None:
        with open(self.token_file, 'w') as f:
            json.dump(self.tokens, f, indent=2)

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime
        return datetime.now().isoformat()
