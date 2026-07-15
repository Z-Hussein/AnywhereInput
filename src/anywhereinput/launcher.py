"""CLI launcher - main(), menus, tunnel checks, argparse."""

import argparse
import asyncio
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from anywhereinput import __version__, safe_print

TUNNEL_CHOICES = ["cloudflare", "tailscale", "pinggy", "zrok2", "local"]


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
    safe_print()
    safe_print("=" * 55)
    safe_print("  AnywhereInput v{} - Remote Control Your PC".format(__version__))
    safe_print("        by AnywhereInput.com Github: @Z-Hussein")
    safe_print("=" * 55)


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


def main():
    from .server_core import AnywhereInputServer

    class ModernHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=34, width=100)

    parser = argparse.ArgumentParser(
        prog="anywhereinput",
        usage=(
            "anywhereinput [--tunnel {cloudflare,tailscale,pinggy,zrok2,local}]"
            " [--host HOST] [--port PORT]\n"
            "              [--fps FPS] [--quality QUALITY] [--scale SCALE]\n"
            "              [--monitor MONITOR] [--no-capture] [--help-tunnels]"
            " [--version]\n\n"
            "Quick Start:\n"
            "  anywhereinput                      Start interactive launcher\n"
            "  anywhereinput --tunnel cloudflare Start immediately with Cloudflare\n"
            "  anywhereinput --tunnel local      Start local-only mode (no tunnel)\n"
            "  anywhereinput --help-tunnels      Show tunnel provider quick help"
        ),
        description=(
            "Control your PC from any browser. No app install, no account,"
            " no cloud dependency."
        ),
        epilog="\n".join(
            [
                "EXAMPLES:",
                "  anywhereinput",
                "    → (interactive menu)",
                "",
                "  anywhereinput --tunnel cloudflare",
                "    → Start with Cloudflare directly",
                "",
                "  anywhereinput --fps 30 --quality 75 --scale 0.7",
                "    → Lower bandwidth (slower capture, lower quality,"
                " smaller stream)",
                "",
                "  anywhereinput --tunnel tailscale",
                "    → Use Tailscale for peer-to-peer control",
                "",
                "  anywhereinput --tunnel local",
                "    → Run on local network only (no tunnel)",
                "",
                "OTHER COMMANDS:",
                "  anywhereinput --help",
                "    → Show all options and examples",
                "",
                "  anywhereinput --help-tunnels",
                "    → Show tunnel-specific quick help",
                "",
                "  anywhereinput --version",
                "    → Show installed version",
                "",
                "  anywhereinput --app",
                "    → Open desktop admin app (PyQt6 GUI)",
                "",
                "TUNNEL PROVIDERS:",
                "  cloudflare  → Free, no account, auto-downloaded,"
                " random URL per session",
                "  tailscale   → Free tailnet P2P (requires account +"
                " same tailnet on both devices)",
                "  pinggy      → Free SSH tunnel (60 min timeout,"
                " behind firewalls OK)",
                "  zrok2       → Free with limits (5 GB/day, open-source)",
                "  local       → Local network only (same WiFi/LAN, no tunnel)",
                "",
                "PROJECT:",
                "  GitHub: https://github.com/Z-Hussein/AnywhereInput",
                "  PyPI: https://pypi.org/project/anywhereinput/",
                "  Docs: https://github.com/Z-Hussein/AnywhereInput" "/tree/main/docs",
            ]
        ),
        formatter_class=ModernHelpFormatter,
    )
    network = parser.add_argument_group("Network")
    network.add_argument("--host", default="127.0.0.1", help="Bind address")
    network.add_argument("--port", type=int, default=8008, help="Server port")

    streaming = parser.add_argument_group("Streaming")
    streaming.add_argument("--fps", type=int, default=120, help="Capture FPS (1-120)")
    streaming.add_argument(
        "--quality",
        type=int,
        default=40,
        help=(
            "JPEG quality for low latency (1-95). Lower = faster encode/decode"
            " but blurrier. Default 40 is optimal for remote control."
        ),
    )
    streaming.add_argument(
        "--scale",
        type=float,
        default=0.5,
        help=(
            "Scale factor for capture (0.1-1.0). Lower = smaller image = much"
            " less data to transmit. 0.5 = half resolution."
        ),
    )
    streaming.add_argument(
        "--monitor", type=int, default=0, help="Monitor index: 0=auto, 1+=fixed"
    )
    streaming.add_argument(
        "--no-capture", action="store_true", help="Disable screen capture"
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

    args = parser.parse_args()

    if args.app:
        from .admin_app import run_admin_app

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

    async def _run():
        selected_tunnel = None if args.tunnel == "local" else args.tunnel
        print(
            f"[DEBUG] Starting server with tunnel_provider={selected_tunnel}",
            file=sys.stderr,
        )
        try:
            await server.start(tunnel_provider=selected_tunnel)
            print("[DEBUG] server.start() returned", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] Exception in start(): {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            raise

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        safe_print(f"❌ Server error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        server._running = False
        server.mouse_worker.stop()
        if server._capture_task:
            server._capture_task.cancel()

        # Clear tokens on shutdown
        server.token_manager.clear_tokens()
        safe_print("[TokenManager] Tokens cleared on shutdown")

        server.tunnel_manager.stop()

        async def _cleanup_clients():
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

        server.screen.close()
        safe_print("\n✅ Server stopped")
        loop.close()
