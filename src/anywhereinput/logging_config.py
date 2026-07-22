"""Logging configuration for AnywhereInput - structured logging with console/file handlers."""

import logging
import logging.handlers
import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Any


class WindowsSafeStreamHandler(logging.StreamHandler):
    """Stream handler that safely handles Windows console encoding issues."""

    def __init__(self, stream=None):
        super().__init__(stream)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            enc = getattr(stream, "encoding", None) or "utf-8"
            encoded = msg.encode(enc, errors="replace").decode(enc, errors="replace")
            stream.write(encoded + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def get_log_dir() -> Path:
    """Get the log directory, creating it if necessary.

    Uses project directory if running from source (for development),
    otherwise uses platform-appropriate user log directory.
    """
    # Check if we're running from the project source directory
    project_root = (
        Path(__file__).resolve().parents[2]
    )  # src/anywhereinput/logging_config.py -> project root
    project_logs = project_root / "logs"

    # If we're in the project source tree (has pyproject.toml), use project logs
    if (project_root / "pyproject.toml").exists():
        project_logs.mkdir(parents=True, exist_ok=True)
        return project_logs

    # Otherwise use platform-appropriate user log directory
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    else:
        base = Path.home() / ".local" / "share"
    log_dir = base / "AnywhereInput" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    level: str = "INFO",
    log_file: bool = True,
    console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Whether to enable file logging
        console: Whether to enable console logging
        max_bytes: Max size of each log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        The configured root logger
    """
    root_logger = logging.getLogger()
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Silence noisy third-party loggers unless DEBUG level
    if log_level > logging.DEBUG:
        logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
        logging.getLogger("aiohttp.server").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("aiohttp.client").setLevel(logging.WARNING)
        logging.getLogger("aiohttp.web").setLevel(logging.WARNING)

    # Our app loggers always respect the configured level
    logging.getLogger("anywhereinput").setLevel(log_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if console:
        console_handler = WindowsSafeStreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        log_path = get_log_dir() / "anywhereinput.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
        root_logger.addHandler(file_handler)

    return root_logger


# ─── Audit Logging ───


class AuditLogger:
    """Persistent audit log for security-relevant events.

    Writes JSON lines to a dedicated rotating audit log file.
    Each entry includes timestamp, event type, actor (IP/token), and details.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or get_log_dir()
        self.audit_path = self.log_dir / "audit.log"
        self._handler: Optional[logging.handlers.RotatingFileHandler] = None
        self._setup_audit_logger()

    def _setup_audit_logger(self) -> None:
        """Configure the audit logger with its own handler."""
        audit_logger = logging.getLogger("anywhereinput.audit")
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False  # Don't bubble to root logger

        # Clear any existing handlers
        for handler in audit_logger.handlers[:]:
            audit_logger.removeHandler(handler)

        # Rotating file handler: 5 MB × 10 files = 50 MB total
        self._handler = logging.handlers.RotatingFileHandler(
            self.audit_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        # JSON formatter for machine parsing
        formatter = logging.Formatter(
            fmt="%(message)s",  # We'll format as JSON in the log method
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._handler.setFormatter(formatter)
        self._handler.setLevel(logging.INFO)
        audit_logger.addHandler(self._handler)
        self.logger = audit_logger

    def _log(
        self, event_type: str, actor: str, details: dict, level: int = logging.INFO
    ) -> None:
        """Write a structured audit log entry."""
        entry = {
            "timestamp": time.time(),
            "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "event": event_type,
            "actor": actor,
            "details": details,
        }
        # Use extra to pass the JSON string
        self.logger.log(level, json.dumps(entry, separators=(",", ":")))

    # ─── Token Events ───

    def token_created(
        self,
        token: str,
        name: str,
        permissions: list,
        allowed_ips: list,
        creator_ip: str,
    ) -> None:
        """Log token creation."""
        self._log(
            "token.created",
            creator_ip,
            {
                "token_prefix": token[:12] + "...",
                "name": name,
                "permissions": permissions,
                "allowed_ips": allowed_ips,
            },
        )

    def token_revoked(self, token: str, revoker_ip: str, reason: str = "") -> None:
        """Log token revocation."""
        self._log(
            "token.revoked",
            revoker_ip,
            {
                "token_prefix": token[:12] + "...",
                "reason": reason,
            },
        )

    def token_rotated(self, old_token: str, new_token: str, rotator_ip: str) -> None:
        """Log token rotation."""
        self._log(
            "token.rotated",
            rotator_ip,
            {
                "old_token_prefix": old_token[:12] + "...",
                "new_token_prefix": new_token[:12] + "...",
            },
        )

    def token_validated(
        self, token: str, client_ip: str, success: bool, reason: str = ""
    ) -> None:
        """Log token validation attempt."""
        self._log(
            "token.validated",
            client_ip,
            {
                "token_prefix": token[:12] + "...",
                "success": success,
                "reason": reason,
            },
            level=logging.INFO if success else logging.WARNING,
        )

    # ─── Client Events ───

    def client_connected(self, client_ip: str, token: str, client_id: str) -> None:
        """Log client WebSocket connection."""
        self._log(
            "client.connected",
            client_ip,
            {
                "token_prefix": token[:12] + "...",
                "client_id": client_id,
            },
        )

    def client_disconnected(
        self, client_ip: str, token: str, client_id: str, reason: str = ""
    ) -> None:
        """Log client WebSocket disconnection."""
        self._log(
            "client.disconnected",
            client_ip,
            {
                "token_prefix": token[:12] + "...",
                "client_id": client_id,
                "reason": reason,
            },
        )

    def client_kicked(
        self, client_ip: str, token: str, kicker_ip: str, client_id: str
    ) -> None:
        """Log client kick event."""
        self._log(
            "client.kicked",
            kicker_ip,
            {
                "target_ip": client_ip,
                "token_prefix": token[:12] + "...",
                "client_id": client_id,
            },
            level=logging.WARNING,
        )

    def ip_blocked(self, ip: str, token: str, blocker_ip: str) -> None:
        """Log IP added to block list."""
        self._log(
            "ip.blocked",
            blocker_ip,
            {
                "blocked_ip": ip,
                "token_prefix": token[:12] + "...",
            },
            level=logging.WARNING,
        )

    def ip_unblocked(self, ip: str, token: str, unblocker_ip: str) -> None:
        """Log IP removed from block list."""
        self._log(
            "ip.unblocked",
            unblocker_ip,
            {
                "unblocked_ip": ip,
                "token_prefix": token[:12] + "...",
            },
        )

    # ─── Connection Request Events ───

    def connection_requested(
        self, client_ip: str, client_name: str, request_id: str
    ) -> None:
        """Log new connection request."""
        self._log(
            "connection.requested",
            client_ip,
            {
                "client_name": client_name,
                "request_id": request_id,
            },
        )

    def connection_approved(
        self, request_id: str, approver_ip: str, token: str, permissions: list
    ) -> None:
        """Log connection request approval."""
        self._log(
            "connection.approved",
            approver_ip,
            {
                "request_id": request_id,
                "token_prefix": token[:12] + "...",
                "permissions": permissions,
            },
        )

    def connection_declined(self, request_id: str, decliner_ip: str) -> None:
        """Log connection request decline."""
        self._log(
            "connection.declined",
            decliner_ip,
            {
                "request_id": request_id,
            },
        )

    # ─── Admin Configuration Events ───

    def admin_config_changed(
        self, admin_ip: str, setting: str, old_value: Any, new_value: Any
    ) -> None:
        """Log admin configuration change."""
        self._log(
            "admin.config_changed",
            admin_ip,
            {
                "setting": setting,
                "old_value": str(old_value),
                "new_value": str(new_value),
            },
        )


# Module-level singleton
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance, initializing if needed."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logging() -> AuditLogger:
    """Initialize and return the audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger()
    return _audit_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)


# Backward compatibility: safe_print replacement
def safe_print(*args, **kwargs):
    """Legacy safe_print - now logs to INFO level."""
    logger = logging.getLogger("anywhereinput.legacy")
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    msg = sep.join(str(arg) for arg in args) + end
    logger.info(msg.strip())


def safe_print_stderr(*args, **kwargs):
    """Legacy safe_print_stderr - now logs to WARNING level."""
    logger = logging.getLogger("anywhereinput.legacy")
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    msg = sep.join(str(arg) for arg in args) + end
    logger.warning(msg.strip())


def raw_print(*args, **kwargs):
    """Direct terminal output without logging formatting.
    Handles Windows encoding issues but prints clean to stdout.
    """
    import sys

    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    msg = sep.join(str(arg) for arg in args) + end
    try:
        enc = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(msg.encode(enc, errors="replace"))
        sys.stdout.flush()
    except Exception:
        sys.stdout.write(msg)
        sys.stdout.flush()


def configure_from_args(args) -> None:
    """Configure logging from parsed CLI arguments."""
    # Determine log level from verbose count and explicit log-level
    verbose = getattr(args, "verbose", 0)
    if verbose >= 1:
        level = "DEBUG"
    else:
        level = getattr(args, "log_level", "INFO")

    # --quiet overrides console output but not file logging
    console = not getattr(args, "quiet", False)
    log_file = not getattr(args, "no_log_file", False)

    setup_logging(
        level=level,
        log_file=log_file,
        console=console,
    )


def add_logging_args(parser) -> None:
    """Add logging-related arguments to an ArgumentParser."""
    logging_group = parser.add_argument_group("Logging")
    logging_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    logging_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity: -v for DEBUG, -vv for more verbose",
    )
    logging_group.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging",
    )
    logging_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output (only log to file)",
    )
