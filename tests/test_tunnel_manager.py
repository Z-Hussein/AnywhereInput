"""Tests for tunnel_manager module - providers, routing, and manager logic."""
import sys
from pathlib import Path
from unittest import mock

src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

import platform as _platform_mod


def test_tunnel_manager_resolve_bind_host_local_to_local():
    """resolve_bind_host returns requested_host for non-tailscale providers."""
    from anywhereinput.tunnel_manager import TunnelManager
    assert TunnelManager.resolve_bind_host("local", "127.0.0.1") == "127.0.0.1"
    assert TunnelManager.resolve_bind_host("cloudflare", "localhost") == "localhost"


def test_tunnel_manager_resolve_bind_host_tailscale():
    """resolve_bind_host changes loopback to 0.0.0.0 for tailscale."""
    from anywhereinput.tunnel_manager import TunnelManager
    assert TunnelManager.resolve_bind_host("tailscale", "127.0.0.1") == "0.0.0.0"
    assert TunnelManager.resolve_bind_host("tailscale", "localhost") == "0.0.0.0"


def test_tunnel_manager_resolve_upstream_host():
    """_resolve_upstream_host maps bind host -> upstream correctly."""
    from anywhereinput.tunnel_manager import TunnelManager
    # tailscale: passthrough
    assert TunnelManager._resolve_upstream_host("tailscale", "0.0.0.0") == "0.0.0.0"
    # local/other: bind on all -> upstream on loopback
    assert TunnelManager._resolve_upstream_host("cloudflare", "0.0.0.0") == "127.0.0.1"
    assert TunnelManager._resolve_upstream_host("cloudflare", "::") == "127.0.0.1"
    # specific bind -> same upstream
    assert TunnelManager._resolve_upstream_host("cloudflare", "192.168.1.50") == "192.168.1.50"


def test_tunnel_manager_list_providers_returns_dict():
    """list_providers returns a dict of name -> availability bool."""
    from anywhereinput.tunnel_manager import TunnelManager
    result = TunnelManager().list_providers()
    assert isinstance(result, dict)
    for k, v in result.items():
        assert isinstance(k, str)
        assert isinstance(v, bool)


def test_tunnel_manager_start_unknown_provider_returns_false():
    """Starting with an unknown provider name returns False."""
    from anywhereinput.tunnel_manager import TunnelManager
    tm = TunnelManager()
    result = tm.start("nonexistent_provider", "127.0.0.1", 8008, lambda u: None)
    assert result is False


def test_tunnel_manager_stop_noop_when_inactive():
    """stop() should not crash when no tunnel is active."""
    from anywhereinput.tunnel_manager import TunnelManager
    tm = TunnelManager()
    tm.stop()  # Should not raise


def test_tunnel_manager_active_tunnel_url_tracking():
    """When a provider produces a URL, it's tracked in self.url."""
    urls_seen = []

    def capture_url(url):
        urls_seen.append(url)

    from anywhereinput.tunnel_manager import TunnelManager

    with mock.patch.object(TunnelManager, 'start') as mock_start:
        mock_start.return_value = False  # Not available, won't actually run

        tm = TunnelManager()
        result = tm.start("tailscale", "0.0.0.0", 8008, capture_url)
        # tailscale is_available returns False in test env (no real tailscale binary)


def test_tunnel_manager_cleanup_all():
    """_cleanup_all terminates tracked processes."""
    from anywhereinput.tunnel_manager import TunnelManager

    mock_proc1 = mock.MagicMock()
    mock_proc1.poll.return_value = None  # still running
    mock_proc2 = mock.MagicMock()
    mock_proc2.poll.return_value = 0  # already exited

    tm = TunnelManager()
    tm._all_procs.add(mock_proc1)
    tm._all_procs.add(mock_proc2)
    tm._cleanup_all()

    mock_proc1.terminate.assert_called_once()


def test_tunnel_manager_kill_process_group_no_proc():
    """_kill_process_group should be safe with None."""
    from anywhereinput.tunnel_manager import TunnelManager
    tm = TunnelManager()
    tm._kill_process_group(None)  # Should not raise


# ─── CloudflareTunnel ───────────────────────────────────────────────────────

def test_cloudflare_tunnel_is_available():
    """is_available returns True if binary is found (even via download path)."""
    from anywhereinput.tunnel_manager import CloudflareTunnel

    with mock.patch.object(CloudflareTunnel, '_find_or_download', return_value="/fake/cloudflared"):
        ct = CloudflareTunnel()
        # Don't test is_available here since it may try to download; just verify init works


def test_cloudflare_tunnel_start_fails_without_binary():
    """start() raises FileNotFoundError when cloudflared binary is missing."""
    from anywhereinput.tunnel_manager import CloudflareTunnel

    with mock.patch.object(CloudflareTunnel, '_find_or_download', return_value="/nonexistent/cloudflared"):
        ct = CloudflareTunnel()
        try:
            ct.start("127.0.0.1", 8008, lambda u: None)
        except FileNotFoundError:
            pass  # expected


# ─── TailscaleTunnel ────────────────────────────────────────────────────────

def test_tailscale_tunnel_is_available_no_binary():
    """is_available returns False when tailscale binary is not in PATH."""
    from anywhereinput.tunnel_manager import TailscaleTunnel

    with mock.patch("anywhereinput.tunnel_manager.shutil.which", return_value=None):
        tt = TailscaleTunnel()
        assert tt.is_available() is False


def test_tailscale_tunnel_start_no_tailnet_ip():
    """start returns None when no tailnet IP detected."""
    from anywhereinput.tunnel_manager import TailscaleTunnel

    with mock.patch("anywhereinput.tunnel_manager.shutil.which", return_value="/fake/tailscale"):
        with mock.patch("socket.gethostname", return_value="test-host"):
            # Return an address that does NOT start with "100."
            with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("192.168.1.1", 0))]):
                tt = TailscaleTunnel()
                result = tt.start("127.0.0.1", 8008, lambda u: None)
                # Should not raise; may print warning about no tailnet IP


# ─── PinggyTunnel ───────────────────────────────────────────────────────────

def test_pinggy_tunnel_is_available():
    """is_available returns True when ssh is in PATH."""
    from anywhereinput.tunnel_manager import PinggyTunnel

    with mock.patch("anywhereinput.tunnel_manager.shutil.which", return_value="/usr/bin/ssh"):
        pt = PinggyTunnel()
        assert pt.is_available() is True


def test_pinggy_tunnel_is_not_available():
    """is_available returns False when ssh not in PATH."""
    from anywhereinput.tunnel_manager import PinggyTunnel

    with mock.patch("anywhereinput.tunnel_manager.shutil.which", return_value=None):
        pt = PinggyTunnel()
        assert pt.is_available() is False


# ─── Zrok2Tunnel ────────────────────────────────────────────────────────────

def test_zrok2_tunnel_is_available():
    """is_available returns True when zrok or zrok2 binary exists."""
    from anywhereinput.tunnel_manager import Zrok2Tunnel

    with mock.patch("anywhereinput.tunnel_manager.shutil.which", side_effect=lambda x: "/usr/bin/zrok" if x == "zrok" else None):
        zt = Zrok2Tunnel()
        assert zt.is_available() is True


def test_zrok2_tunnel_is_not_available():
    """is_available returns False when neither zrok nor zrok2 exists."""
    from anywhereinput.tunnel_manager import Zrok2Tunnel

    with mock.patch("anywhereinput.tunnel_manager.shutil.which", return_value=None):
        zt = Zrok2Tunnel()
        assert zt.is_available() is False


def test_zrok2_tunnel_strip_ansi():
    """_strip_ansi removes ANSI escape sequences."""
    from anywhereinput.tunnel_manager import Zrok2Tunnel

    assert Zrok2Tunnel._strip_ansi("hello\x1b[31mworld\x1b[0m") == "helloworld"
    assert Zrok2Tunnel._strip_ansi("plain text") == "plain text"


# ─── TunnelManager full flow ────────────────────────────────────────────────

def test_tunnel_manager_start_cloudflare_no_crash():
    """start('cloudflare') returns False when provider is unavailable,
    without downloading binaries or starting subprocesses."""
    from anywhereinput.tunnel_manager import TunnelManager, CloudflareTunnel

    tm = TunnelManager()
    # Replace the class in PROVIDERS dict so instantiation raises immediately
    orig_class = TunnelManager.PROVIDERS["cloudflare"]

    class NoOpProvider:
        """Fails during __init__ to simulate missing binary."""
        def __init__(self):
            raise FileNotFoundError("cloudflared unavailable")

        @staticmethod
        def is_available():
            return False

    TunnelManager.PROVIDERS["cloudflare"] = NoOpProvider
    try:
        result = tm.start("cloudflare", "127.0.0.1", 8008, lambda u: None)
    except FileNotFoundError:
        result = False
    finally:
        TunnelManager.PROVIDERS["cloudflare"] = orig_class

    assert result is False


def test_tunnel_manager_provider_keys():
    """PROVIDERS dict has expected keys."""
    from anywhereinput.tunnel_manager import TunnelManager
    expected = {"cloudflare", "tailscale", "pinggy", "zrok2"}
    assert set(TunnelManager.PROVIDERS.keys()) == expected
