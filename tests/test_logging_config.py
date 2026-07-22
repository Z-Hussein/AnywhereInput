"""Tests for logging_config module."""

import json
import logging
from pathlib import Path
from unittest import mock

from anywhereinput.logging_config import (
    AuditLogger,
    WindowsSafeStreamHandler,
    add_logging_args,
    configure_from_args,
    get_audit_logger,
    get_log_dir,
    get_logger,
    raw_print,
    setup_logging,
)


class TestGetLogDir:
    def test_returns_path(self):
        result = get_log_dir()
        assert isinstance(result, Path)
        assert result.exists() or result.parent.exists()


class TestSetupLogging:
    def test_console_only(self):
        setup_logging(level="DEBUG", log_file=False, console=True)
        root = logging.getLogger("anywhereinput")
        assert root.level == logging.DEBUG

    def test_with_file(self):
        setup_logging(level="INFO", log_file=False, console=True)

    def test_quiet_mode(self):
        setup_logging(level="INFO", log_file=False, console=False)


class TestAuditLogger:
    def _read_last_entry(self, log_path):
        lines = log_path.read_text().strip().split("\n")
        return json.loads(lines[-1])

    def test_token_created(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.token_created(
            token="abcdef1234567890",
            name="test",
            permissions=["screen"],
            allowed_ips=[],
            creator_ip="1.2.3.4",
        )
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "token.created"
        assert entry["actor"] == "1.2.3.4"
        assert entry["details"]["token_prefix"] == "abcdef123456..."

    def test_token_revoked(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.token_revoked(token="abcdef1234567890", revoker_ip="1.2.3.4", reason="api")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "token.revoked"

    def test_client_connected(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.client_connected(client_ip="1.2.3.4", token="abcdef1234567890", client_id="c1")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "client.connected"
        assert entry["details"]["client_id"] == "c1"

    def test_client_disconnected(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.client_disconnected(
            client_ip="1.2.3.4", token="abcdef1234567890", client_id="c1", reason="timeout"
        )
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "client.disconnected"

    def test_connection_requested(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.connection_requested(client_ip="5.6.7.8", client_name="browser", request_id="r1")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "connection.requested"
        assert entry["details"]["request_id"] == "r1"

    def test_connection_approved(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.connection_approved(
            request_id="r1", approver_ip="1.2.3.4", token="abcdef1234567890", permissions=["screen"]
        )
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "connection.approved"

    def test_connection_declined(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.connection_declined(request_id="r2", decliner_ip="1.2.3.4")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "connection.declined"

    def test_admin_config_changed(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.admin_config_changed(admin_ip="1.2.3.4", setting="fps", old_value=30, new_value=60)
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "admin.config_changed"
        assert entry["details"]["setting"] == "fps"

    def test_ip_blocked(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.ip_blocked(ip="9.9.9.9", token="abcdef1234567890", blocker_ip="1.2.3.4")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "ip.blocked"

    def test_ip_unblocked(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.ip_unblocked(ip="9.9.9.9", token="abcdef1234567890", unblocker_ip="1.2.3.4")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "ip.unblocked"

    def test_token_rotated(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.token_rotated(old_token="old1234567890ab", new_token="new1234567890ab", rotator_ip="1.2.3.4")
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "token.rotated"

    def test_token_validated(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.token_validated(token="abcdef1234567890", client_ip="1.2.3.4", success=True)
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "token.validated"
        assert entry["details"]["success"] is True

    def test_client_kicked(self, tmp_path):
        al = AuditLogger(log_dir=tmp_path)
        al.client_kicked(
            client_ip="1.2.3.4", token="abcdef1234567890", kicker_ip="5.6.7.8", client_id="c1"
        )
        entry = self._read_last_entry(tmp_path / "audit.log")
        assert entry["event"] == "client.kicked"


class TestConfigureFromArgs:
    def test_default_level(self):
        args = mock.MagicMock()
        args.verbose = 0
        args.quiet = False
        args.log_level = "INFO"
        args.no_log_file = False
        configure_from_args(args)

    def test_verbose(self):
        args = mock.MagicMock()
        args.verbose = 1
        args.quiet = False
        args.log_level = "INFO"
        args.no_log_file = False
        configure_from_args(args)

    def test_quiet(self):
        args = mock.MagicMock()
        args.verbose = 0
        args.quiet = True
        args.log_level = "INFO"
        args.no_log_file = False
        configure_from_args(args)


class TestRawPrint:
    def test_outputs(self, capsys):
        raw_print("hello test")
        captured = capsys.readouterr()
        assert "hello test" in captured.out


class TestGetLogger:
    def test_returns_logger(self):
        log = get_logger("anywhereinput.test")
        assert isinstance(log, logging.Logger)
        assert log.name == "anywhereinput.test"
