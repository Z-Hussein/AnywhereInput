"""CLI launcher - main(), menus, tunnel checks, argparse."""

import argparse
import asyncio
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from anywhereinput import __version__
from anywhereinput.logging_config import (
    configure_from_args,
    get_logger,
    add_logging_args,
    safe_print,
    raw_print,
)
from ._constants import (
    TUNNEL_CHOICES,
    DEFAULT_HOST,
    DEFAULT_PORT,
    LOW_BW_FPS,
    LOW_BW_QUALITY,
    LOW_BW_SCALE,
    DEFAULT_FPS,
    DEFAULT_QUALITY,
    DEFAULT_SCALE,
)
from .config_loader import load_settings, get_setting

log = get_logger(__name__)


def _check_cloudflare() -> bool:
    return Path("./cloudflared").is_file() or shutil.which("cloudflared") is not None


def _check_tailscale() -> bool:
    tailscale = shutil.which("tailscale")
    if not tailscale:
        return False
    try:
        result = subprocess.run(
            [tailscale, "status", "--json"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_pinggy() -> bool:
    return shutil.which("ssh") is not None


def _check_zrok() -> bool:
    return shutil.which("zrok") is not None or shutil.which("zrok2") is not None


def _status_mark(ok: bool, uncertain: bool = False) -> str:
    if ok:
        return "[OK]"
    return "[?]" if uncertain else "[X]"


def _print_launcher_banner() -> None:
    raw_print()
    raw_print("  ┌──────────────────────────────────────────────────┐")
    raw_print(
        "  │  AnywhereInput v{}                              │".format(__version__)
    )
    raw_print("  │  Remote control your PC from any browser         │")
    raw_print("  └──────────────────────────────────────────────────┘")
    raw_print()


def _print_start_menu() -> str:
    cf_ok = _status_mark(_check_cloudflare())
    ts_ok = _status_mark(_check_tailscale(), uncertain=True)
    pg_ok = _status_mark(_check_pinggy(), uncertain=True)
    zr_ok = _status_mark(_check_zrok(), uncertain=True)

    while True:
        _print_launcher_banner()
        safe_print("\nSelect tunnel provider:")
        safe_print(f"  [1] Cloudflare Tunnel (Recommended) {cf_ok}")
        safe_print(f"  [2] Tailscale (tailnet P2P) {ts_ok}")
        safe_print(f"  [3] Pinggy.io (SSH tunnel) {pg_ok}")
        safe_print(f"  [4] Zrok2 {zr_ok}")
        safe_print("  [5] Local only")
        safe_print("  [S] Setup / Repair")
        safe_print("  [Q] Quit")
        choice = input("\nEnter choice (1-5, S, Q): ").strip()

        mapping = {
            "1": "cloudflare",
            "2": "tailscale",
            "3": "pinggy",
            "4": "zrok2",
            "5": "local",
        }
        if choice in mapping:
            return mapping[choice]
        if choice.lower() == "s":
            return "setup"
        if choice.lower() == "q":
            return "quit"
        safe_print("\nInvalid choice. Please try again.")


def _run_setup_repair() -> int:
    project_root = Path(__file__).resolve().parents[2]
    if platform.system() == "Windows":
        setup_script = project_root / "scripts" / "windows" / "setup.bat"
    else:
        setup_script = project_root / "scripts" / "unix" / "setup.sh"

    if setup_script.exists():
        safe_print(f"\n[Setup] Running: {setup_script}")
        cmd = (
            [str(setup_script)]
            if setup_script.suffix != ".bat"
            else ["cmd", "/c", str(setup_script)]
        )
        try:
            return subprocess.call(cmd, cwd=str(project_root))
        except Exception as e:
            safe_print(f"[Setup] Failed to run setup script: {e}")
            return 1

    safe_print("\n[Setup] No setup script found in this installation.")
    safe_print("Try one of these:")
    safe_print("  pip install --upgrade anywhereinput")
    safe_print("  pipx upgrade anywhereinput")
    return 1


def _print_tunnel_help() -> None:
    safe_print("\nTunnel Quick Help")
    safe_print("  cloudflare  Free, no account, random URL each run")
    safe_print("  tailscale   Tailnet P2P, account + same tailnet required")
    safe_print("  pinggy      SSH-based tunnel, good behind strict firewalls")
    safe_print("  zrok2       Open-source tunnel with free-tier limits")
    safe_print("  local       No tunnel, same network only (--tunnel local)")


def create_parser(cfg: dict | None = None) -> argparse.ArgumentParser:
    """Build the CLI argument parser with YAML-backed defaults.

    Args:
        cfg: Loaded YAML config dict. If None, loaded from settings files.
    """
    if cfg is None:
        cfg = load_settings()

    # Resolve defaults from YAML config (CLI args override these)
    _host_default = get_setting(cfg, "server", "host", default=DEFAULT_HOST)
    _port_default = get_setting(cfg, "server", "port", default=DEFAULT_PORT)
    _fps_default = get_setting(cfg, "screen_capture", "fps", default=DEFAULT_FPS)
    _quality_default = get_setting(
        cfg, "screen_capture", "quality", default=DEFAULT_QUALITY
    )
    _scale_default = get_setting(cfg, "screen_capture", "scale", default=DEFAULT_SCALE)

    class ModernHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=34, width=100)

    parser = argparse.ArgumentParser(
        prog="anywhereinput",
        usage=(
            "anywhereinput [--tunnel PROVIDER] [--host HOST] [--port PORT]\n"
            "              [--fps FPS] [--quality Q] [--scale S]\n"
            "              [--monitor MONITOR] [--no-capture]\n"
            "              [--help-tunnels] [--log-level LVL] [-v] [--quiet]\n"
            "              [--app] [--version]\n\n"
            "Quick start:\n"
            "  anywhereinput                        Interactive launcher\n"
            "  anywhereinput --tunnel cloudflare    Public access (zero-config)\n"
            "  anywhereinput --tunnel local         LAN only\n"
            "  anywhereinput --app                  Desktop admin GUI\n"
        ),
        description=(
            "Control your PC from any browser. No app install, no account,"
            " no cloud dependency."
        ),
        epilog="\n".join(
            [
                "EXAMPLES",
                "──────────",
                "  anywhereinput                        Interactive launcher",
                "  anywhereinput --tunnel cloudflare    Public access (zero-config)",
                "  anywhereinput --tunnel local         LAN only, no tunnel",
                "  anywhereinput --app                  Desktop admin GUI",
                "  anywhereinput --help-tunnels         Tunnel comparison",
                "",
                "TUNNELS",
                "──────────",
                "  cloudflare   Free, no account, random URL each run",
                "  tailscale    P2P over Tailnet, stable address",
                "  pinggy       SSH-based, good behind strict firewalls",
                "  zrok2        Open-source, 5 GB/day free tier",
                "  local        Same network only, zero deps",
                "",
                f"STREAMING (default: --fps {_fps_default} --quality {_quality_default} --scale {_scale_default})",
                "──────────",
                "  --fps N          Capture FPS (1-120)",
                "  --quality N      JPEG quality 1-95 (lower = faster, blurrier)",
                "  --scale F        Scale factor 0.1-1.0 (0.5 = half res)",
                "  --monitor N      Monitor index: 0=auto, 1+=fixed",
                "  --no-capture     Disable screen capture",
                "",
                "LOGGING",
                "──────────",
                "  -v, --verbose        DEBUG to console+file (repeat for more)",
                "  --quiet              Console silent, file only",
                "  --log-level LEVEL    DEBUG/INFO/WARNING/ERROR/CRITICAL",
                "  --no-log-file        Disable file logging",
                "",
                "OTHER",
                "──────────",
                "  anywhereinput --app           Desktop admin GUI (tokens, logs)",
                "  anywhereinput --version       Show version",
                "  anywhereinput --help-tunnels  Tunnel comparison",
                "",
                "PROJECT",
                "──────────",
                "  GitHub: https://github.com/Z-Hussein/AnywhereInput",
                "  PyPI:   https://pypi.org/project/anywhereinput/",
            ]
        ),
        formatter_class=ModernHelpFormatter,
    )
    network = parser.add_argument_group("Network")
    network.add_argument(
        "--host",
        default=_host_default,
        help="Bind address",
    )
    network.add_argument(
        "--port",
        type=int,
        default=_port_default,
        help="Server port",
    )

    streaming = parser.add_argument_group("Streaming")
    streaming.add_argument(
        "--fps",
        type=int,
        default=_fps_default,
        help=f"Capture FPS (1-120). Default: {_fps_default}",
    )
    streaming.add_argument(
        "--quality",
        type=int,
        default=_quality_default,
        help=(
            f"JPEG quality for low latency (1-95). Lower = faster encode/decode"
            f" but blurrier. Default: {_quality_default}."
        ),
    )
    streaming.add_argument(
        "--scale",
        type=float,
        default=_scale_default,
        help=(
            f"Scale factor for capture (0.1-1.0). Lower = smaller image = much"
            f" less data to transmit. 0.5 = half resolution. Default: {_scale_default}."
        ),
    )
    streaming.add_argument(
        "--monitor", type=int, default=0, help="Monitor index: 0=auto, 1+=fixed"
    )
    streaming.add_argument(
        "--no-capture", action="store_true", help="Disable screen capture"
    )
    streaming.add_argument(
        "--low-bandwidth",
        action="store_true",
        help="Optimize for mobile data / slow connections (15fps, 60%% quality, half scale). "
        "Adaptive streaming auto-adjusts further.",
    )

    connectivity = parser.add_argument_group("Connectivity")
    connectivity.add_argument(
        "--tunnel",
        choices=TUNNEL_CHOICES,
        help="Tunnel provider (default: interactive menu)",
    )
    connectivity.add_argument(
        "--help-tunnels",
        action="store_true",
        help="Show tunnel quick help and exit",
    )

    parser.add_argument(
        "--app",
        action="store_true",
        help="Open the desktop admin app (PyQt6 GUI) instead of the terminal launcher.",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # Logging arguments
    add_logging_args(parser)

    return parser


def main() -> None:
    from .server import AnywhereInputServer

    parser = create_parser()
    # Use parse_known_args so 'config' subcommand doesn't fail on unknown flags
    args, remaining = parser.parse_known_args()

    # Handle config subcommand
    if remaining and remaining[0] == "config":
        from .config_cmd import (
            _cmd_init_run,
            _cmd_view_run,
            _cmd_edit_run,
            _cmd_list_run,
        )
        import argparse as _ap

        subcmd = remaining[1] if len(remaining) > 1 else "list"
        # Rebuild a proper namespace for the config subcommands
        cfg_args = _ap.Namespace(
            settings="--settings" in remaining,
            recovery="--recovery" in remaining,
            all="--all" in remaining,
        )
        if subcmd == "init":
            _cmd_init_run(cfg_args)
        elif subcmd == "view":
            _cmd_view_run(cfg_args)
        elif subcmd == "edit":
            _cmd_edit_run(cfg_args)
        elif subcmd == "list":
            _cmd_list_run(cfg_args)
        else:
            print("Usage: anywhereinput config <command>")
            print("Commands:")
            print("  init          Generate default config files from examples")
            print("  init --recovery   Also create recovery.yaml")
            print("  list          List available configuration files")
            print("  view          Show current config file contents")
            print("  edit          Open a config file in $EDITOR")
        return

    # Configure logging from args
    configure_from_args(args)

    if args.app:
        from .admin import run_admin_app

        run_admin_app()
        return

    if args.help_tunnels:
        _print_tunnel_help()
        return

    argv = sys.argv[1:]
    if not argv:
        if sys.stdin and sys.stdin.isatty():
            while True:
                selected = _print_start_menu()
                if selected == "quit":
                    return
                if selected == "setup":
                    _run_setup_repair()
                    continue
                args.tunnel = None if selected == "local" else selected
                break
        else:
            _print_launcher_banner()
            safe_print(
                "No interactive terminal detected; defaulting to Cloudflare Tunnel."
            )
            args.tunnel = "cloudflare"

    # Apply low-bandwidth preset if requested (overrides individual settings)
    if args.low_bandwidth:
        args.fps = LOW_BW_FPS
        args.quality = LOW_BW_QUALITY
        args.scale = LOW_BW_SCALE
        log.info(
            "[LowBandwidth] Using mobile-optimized: %dfps, q%d, scale %.1f",
            args.fps,
            args.quality,
            args.scale,
        )

    server = AnywhereInputServer(
        host=args.host,
        port=args.port,
        fps=args.fps,
        quality=args.quality,
        scale=args.scale,
        no_capture=args.no_capture,
        monitor=args.monitor,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run() -> None:
        selected_tunnel = None if args.tunnel == "local" else args.tunnel
        log.debug("Starting server with tunnel_provider=%s", selected_tunnel)
        try:
            await server.start(tunnel_provider=selected_tunnel)
            log.debug("server.start() returned")
        except Exception as e:
            log.exception("Exception in start(): %s", e)
            raise

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        log.error("Server error: %s", e)
        import traceback

        traceback.print_exc()
    finally:
        server._running = False
        server.mouse_worker.stop()
        if server._capture_task:
            server._capture_task.cancel()

        # Clear tokens on shutdown — approved tokens are one-time use and should not persist across restarts
        server.token_manager.clear_tokens()
        log.info("[TokenManager] Tokens cleared on shutdown")

        server.tunnel_manager.stop()

        async def _cleanup_clients() -> None:
            async with server.clients_lock:
                for ws in list(server.clients):
                    try:
                        await ws.close()
                    except BaseException:
                        pass
                server.clients.clear()

        try:
            loop.run_until_complete(asyncio.wait_for(_cleanup_clients(), timeout=2))
        except BaseException:
            pass

        if server.runner:
            try:
                loop.run_until_complete(server.runner.cleanup())
            except Exception:
                pass

        try:
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        except Exception:
            pass

        server.screen.close()  # type: ignore[attr-defined]
        log.info("Server stopped")
        loop.close()
