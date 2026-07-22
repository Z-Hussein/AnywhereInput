"""Tests for CLI argument parsing."""

import pytest

from anywhereinput._constants import (
    DEFAULT_FPS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_QUALITY,
    DEFAULT_SCALE,
    LOW_BW_FPS,
    LOW_BW_QUALITY,
    LOW_BW_SCALE,
    TUNNEL_CHOICES,
)
from anywhereinput.launcher import create_parser


@pytest.fixture
def parser():
    return create_parser(cfg={})


class TestDefaults:
    def test_host(self, parser):
        args = parser.parse_args([])
        assert args.host == DEFAULT_HOST

    def test_port(self, parser):
        args = parser.parse_args([])
        assert args.port == DEFAULT_PORT

    def test_fps(self, parser):
        args = parser.parse_args([])
        assert args.fps == DEFAULT_FPS

    def test_quality(self, parser):
        args = parser.parse_args([])
        assert args.quality == DEFAULT_QUALITY

    def test_scale(self, parser):
        args = parser.parse_args([])
        assert args.scale == DEFAULT_SCALE

    def test_monitor(self, parser):
        args = parser.parse_args([])
        assert args.monitor == 0

    def test_no_capture(self, parser):
        args = parser.parse_args([])
        assert args.no_capture is False

    def test_low_bandwidth(self, parser):
        args = parser.parse_args([])
        assert args.low_bandwidth is False

    def test_tunnel(self, parser):
        args = parser.parse_args([])
        assert args.tunnel is None

    def test_app(self, parser):
        args = parser.parse_args([])
        assert args.app is False

    def test_verbose(self, parser):
        args = parser.parse_args([])
        assert args.verbose == 0

    def test_quiet(self, parser):
        args = parser.parse_args([])
        assert args.quiet is False

    def test_log_level(self, parser):
        args = parser.parse_args([])
        assert args.log_level == "INFO"

    def test_no_log_file(self, parser):
        args = parser.parse_args([])
        assert args.no_log_file is False

    def test_help_tunnels(self, parser):
        args = parser.parse_args([])
        assert args.help_tunnels is False


class TestCustomValues:
    def test_host(self, parser):
        args = parser.parse_args(["--host", "0.0.0.0"])
        assert args.host == "0.0.0.0"

    def test_port(self, parser):
        args = parser.parse_args(["--port", "9090"])
        assert args.port == 9090

    def test_fps(self, parser):
        args = parser.parse_args(["--fps", "30"])
        assert args.fps == 30

    def test_quality(self, parser):
        args = parser.parse_args(["--quality", "50"])
        assert args.quality == 50

    def test_scale(self, parser):
        args = parser.parse_args(["--scale", "0.5"])
        assert args.scale == 0.5

    def test_monitor(self, parser):
        args = parser.parse_args(["--monitor", "2"])
        assert args.monitor == 2

    def test_tunnel(self, parser):
        args = parser.parse_args(["--tunnel", "cloudflare"])
        assert args.tunnel == "cloudflare"

    def test_all_tunnels_valid(self, parser):
        for t in TUNNEL_CHOICES:
            args = parser.parse_args(["--tunnel", t])
            assert args.tunnel == t

    def test_log_level_debug(self, parser):
        args = parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

    def test_log_level_warning(self, parser):
        args = parser.parse_args(["--log-level", "WARNING"])
        assert args.log_level == "WARNING"


class TestFlags:
    def test_no_capture(self, parser):
        args = parser.parse_args(["--no-capture"])
        assert args.no_capture is True

    def test_low_bandwidth(self, parser):
        args = parser.parse_args(["--low-bandwidth"])
        assert args.low_bandwidth is True

    def test_app(self, parser):
        args = parser.parse_args(["--app"])
        assert args.app is True

    def test_quiet(self, parser):
        args = parser.parse_args(["--quiet"])
        assert args.quiet is True

    def test_no_log_file(self, parser):
        args = parser.parse_args(["--no-log-file"])
        assert args.no_log_file is True

    def test_help_tunnels(self, parser):
        args = parser.parse_args(["--help-tunnels"])
        assert args.help_tunnels is True


class TestVerbose:
    def test_single_v(self, parser):
        args = parser.parse_args(["-v"])
        assert args.verbose == 1

    def test_double_v(self, parser):
        args = parser.parse_args(["-vv"])
        assert args.verbose == 2

    def test_long_verbose(self, parser):
        args = parser.parse_args(["--verbose"])
        assert args.verbose == 1

    def test_verbose_plus_short(self, parser):
        args = parser.parse_args(["-v", "-v", "-v"])
        assert args.verbose == 3


class TestCombinedArgs:
    def test_all_streaming(self, parser):
        args = parser.parse_args([
            "--fps", "30", "--quality", "55", "--scale", "0.6", "--monitor", "1"
        ])
        assert args.fps == 30
        assert args.quality == 55
        assert args.scale == 0.6
        assert args.monitor == 1

    def test_network_plus_streaming(self, parser):
        args = parser.parse_args([
            "--host", "0.0.0.0", "--port", "9090", "--tunnel", "local"
        ])
        assert args.host == "0.0.0.0"
        assert args.port == 9090
        assert args.tunnel == "local"

    def test_logging_combined(self, parser):
        args = parser.parse_args(["-v", "--quiet"])
        assert args.verbose == 1
        assert args.quiet is True


class TestInvalidArgs:
    def test_invalid_tunnel(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["--tunnel", "invalid_provider"])

    def test_invalid_log_level(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "INVALID"])


class TestLowBandwidthPresets:
    def test_low_bw_fps(self):
        assert LOW_BW_FPS == 15

    def test_low_bw_quality(self):
        assert LOW_BW_QUALITY == 60

    def test_low_bw_scale(self):
        assert LOW_BW_SCALE == 0.5
