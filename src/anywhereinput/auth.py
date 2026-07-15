"""Token-based authentication manager."""

import secrets
import json
from pathlib import Path
from typing import Dict, Optional, List

# Import safe_print from the server module for error reporting
# This is a circular import guard - safe_print is only used in _save_tokens errors
try:
    from .server import safe_print
except ImportError:
    # Fallback if server module not yet loaded (e.g., during package init)
    def safe_print(*args, **kwargs):
        print(*args, **kwargs)


class TokenManager:
    """Manages secure token generation, validation, and rotation."""

    _DEFAULT_PERMISSIONS = (
        "move",
        "click",
        "scroll",
        "keyboard",
        "screen_toggle",
        "ping",
    )

    @classmethod
    def DEFAULT_PERMISSIONS(cls) -> list:
        """Return a fresh copy of the default permission list.

        The tuple is intentionally immutable so that accidental in-place
        mutation (e.g. ``TokenManager.DEFAULT_PERMISSIONS.append(...)``)
        cannot affect other instances.
        """
        return list(cls._DEFAULT_PERMISSIONS)

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
        self._load_tokens()

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
        import ipaddress

        try:
            client = ipaddress.ip_address(TokenManager._extract_ip(client_ip))
            for allowed in allowed_ips:
                allowed = allowed.strip()
                if not allowed:
                    continue
                try:
                    if "/" in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client in network:
                            return True
                    else:
                        if client == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    continue
        except ValueError:
            pass
        return False

    @staticmethod
    def _extract_ip(client_ip: str) -> str:
        """Extract IP address from stored format:
        - Bracketed IPv6 with port: [::1]:8080 -> ::1
        - Bare IPv6 (no port): 2003:abc::1 or 2003:abc::1%eth0 -> 2003:abc::1
        - IPv4 with port: 192.168.1.1:8080 -> 192.168.1.1
        - Bare IPv4: 192.168.1.1 -> 192.168.1.1
        """
        if client_ip.startswith("["):
            # Bracketed IPv6 with port: [::1]:8080 -> extract ::1
            bracket_end = client_ip.find("]")
            return client_ip[1:bracket_end] if bracket_end > 0 else client_ip
        # Bare IPv6: 2003:abc::1 or 2003:abc::1%eth0 (multiple colons or zone index)
        if client_ip.count(":") >= 2 or "%" in client_ip:
            return client_ip.split("%")[0]  # strip zone index if present
        # IPv4 with port: 192.168.1.1:8080 or bare IP
        return client_ip.split(":")[0] if ":" in client_ip else client_ip

    def _ip_blocked(self, client_ip: str, ip_list: Optional[List[str]] = None) -> bool:
        """Check if client_ip matches any CIDR or exact IP in ip_list (or global blocked_ips)."""
        import ipaddress

        if ip_list is None:
            ip_list = self.blocked_ips
        try:
            client = ipaddress.ip_address(self._extract_ip(client_ip))
            for blocked in ip_list:
                blocked = blocked.strip()
                if not blocked:
                    continue
                try:
                    if "/" in blocked:
                        network = ipaddress.ip_network(blocked, strict=False)
                        if client in network:
                            return True
                    else:
                        if client == ipaddress.ip_address(blocked):
                            return True
                except ValueError:
                    continue
        except ValueError:
            pass
        return False

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
            safe_print(
                f"[TokenManager] WARNING: Could not save tokens to {self.token_file}: {e}"
            )
            self._last_save_error = str(e)

    def clear_tokens(self) -> None:
        """Clear all tokens and remove the token file."""
        self.tokens = {}
        try:
            if self.token_file.exists():
                self.token_file.unlink()
        except Exception as e:
            safe_print(f"[TokenManager] WARNING: Could not remove token file: {e}")

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime

        return datetime.now().isoformat()
