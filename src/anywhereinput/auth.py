"""Token-based authentication manager."""

import json
import secrets
from pathlib import Path
from typing import Dict, Optional, List

from ._ip import ip_allowed, ip_blocked
from ._permissions import get_default_permissions
from .logging_config import get_logger

log = get_logger(__name__)


class TokenManager:
    """Manages secure token generation, validation, and rotation."""

    @classmethod
    def DEFAULT_PERMISSIONS(cls) -> list:
        """Return a fresh copy of the default permission list.

        The tuple is intentionally immutable so that accidental in-place
        mutation (e.g. ``TokenManager.DEFAULT_PERMISSIONS.append(...)``)
        cannot affect other instances.
        """
        return get_default_permissions()

    def __init__(self, token_file: Optional[str] = None):
        # Resolve token file relative to the module's directory
        if token_file is None:
            _module_dir = Path(__file__).resolve().parent
            self.token_file = _module_dir.parent / "trusted_tokens.json"
        elif not Path(token_file).is_absolute():
            # Relative path - resolve against the module parent (project root)
            _module_dir = Path(__file__).resolve().parent
            self.token_file = (_module_dir.parent / token_file).resolve()
        else:
            self.token_file = Path(token_file)
        self.tokens: Dict[str, dict] = {}
        # Global IP block/deny list (applies to all tokens)
        self.blocked_ips: List[str] = []
        # Zero-trust: always start fresh — clear any stale tokens from disk
        self.clear_tokens()

    def generate_token(self, name: str = "auto-generated", length: int = 32) -> str:
        """Generate a new secure random token."""
        token = secrets.token_urlsafe(length)
        self.tokens[token] = {
            "name": name,
            "created": self._timestamp(),
            "permissions": self.DEFAULT_PERMISSIONS(),
        }
        self._save_tokens()
        return token

    def validate(
        self,
        token: str,
        permission: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> bool:
        """Validate a token and optionally check a permission and client IP."""
        if token not in self.tokens:
            return False
        token_data = self.tokens[token]
        # Rejected tokens (e.g. tombstones from revocation) have no permissions — reject immediately
        if not token_data.get("permissions"):
            return False
        if permission and permission not in token_data.get("permissions", []):
            return False
        # Check global block list
        if client_ip and self._ip_blocked(client_ip):
            return False
        # Check token's block list
        blocked_ips = token_data.get("blocked_ips", [])
        if blocked_ips and client_ip:
            if self._ip_blocked(client_ip, blocked_ips):
                return False
        # Check IP allowlist if configured
        allowed_ips = token_data.get("allowed_ips", [])
        if allowed_ips and client_ip:
            if not self._ip_allowed(client_ip, allowed_ips):
                return False
        return True

    @staticmethod
    def _ip_allowed(client_ip: str, allowed_ips: List[str]) -> bool:
        """Check if client_ip matches any CIDR or exact IP in allowed_ips."""
        return ip_allowed(client_ip, allowed_ips)

    def _ip_blocked(self, client_ip: str, ip_list: Optional[List[str]] = None) -> bool:
        """Check if client_ip matches any CIDR or exact IP in ip_list (or global blocked_ips)."""
        if ip_list is None:
            ip_list = self.blocked_ips
        return ip_blocked(client_ip, ip_list)

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
            {
                "name": v["name"],
                "created": v["created"],
                "permissions": v["permissions"],
            }
            for v in self.tokens.values()
        ]

    def _load_tokens(self) -> None:
        if self.token_file.exists():
            try:
                with open(self.token_file, "r") as f:
                    all_tokens = json.load(f)
                    if all_tokens and isinstance(all_tokens, dict):
                        # Support both single-token legacy format and multi-token new format
                        first_val = next(iter(all_tokens.values()))
                        if isinstance(first_val, dict) and "name" in first_val:
                            # Multi-token format
                            self.tokens = {k: v for k, v in all_tokens.items()}
                        else:
                            # Legacy values may not have expected dict structure - normalize them
                            self.tokens = {}
                            for k, v in all_tokens.items():
                                if isinstance(v, dict):
                                    self.tokens[k] = {
                                        "name": v.get("name", "unknown"),
                                        "created": v.get("created", ""),
                                        "permissions": v.get("permissions", []),
                                    }
                                else:
                                    # Non-dict legacy value (e.g. plain string token) - wrap as safe dict
                                    self.tokens[k] = {
                                        "name": "legacy",
                                        "created": "",
                                        "permissions": [],
                                    }
                    elif all_tokens and isinstance(all_tokens, list):
                        # Legacy array format - each item should be a dict with at least an ID
                        self.tokens = {}
                        for item in all_tokens:
                            if isinstance(item, dict):
                                token_val = item.get("token", item.get("id", ""))
                                if token_val:
                                    self.tokens[token_val] = {
                                        "name": item.get("name", "legacy"),
                                        "created": item.get("created", ""),
                                        "permissions": item.get("permissions", []),
                                    }
                    else:
                        self.tokens = {}
            except (json.JSONDecodeError, IOError):
                self.tokens = {}

    def _save_tokens(self) -> None:
        """Save ALL tokens (no truncation)."""
        try:
            with open(self.token_file, "w") as f:
                json.dump(self.tokens, f, indent=2)
        except IOError as e:
            log.warning(
                "[TokenManager] Could not save tokens to %s: %s", self.token_file, e
            )
            self._last_save_error = str(e)

    def clear_tokens(self) -> None:
        """Clear all tokens and remove the token file."""
        self.tokens = {}
        try:
            if self.token_file.exists():
                self.token_file.unlink()
        except Exception as e:
            log.warning("[TokenManager] Could not remove token file: %s", e)

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime

        return datetime.now().isoformat()
