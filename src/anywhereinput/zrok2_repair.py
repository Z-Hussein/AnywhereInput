"""Zrok2 diagnostic and repair tool."""

import shutil
import subprocess
from anywhereinput.logging_config import get_logger
from anywhereinput._safe_print import safe_print, safe_print_stderr

log = get_logger(__name__)


def check_zrok_installation() -> bool:
    """Check if zrok is properly installed."""
    zrok_path = shutil.which("zrok") or shutil.which("zrok2")
    if zrok_path:
        log.info("✅ zrok found: %s", zrok_path)
        safe_print(f"✅ zrok found: {zrok_path}")
        return True
    log.error("❌ zrok not found in PATH")
    safe_print_stderr("❌ zrok not found in PATH")
    return False


def check_zrok_enabled() -> bool:
    """Check if zrok environment is enabled."""
    try:
        result = subprocess.run(
            ["zrok", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            log.info("✅ zrok environment is enabled")
            safe_print("✅ zrok environment is enabled")
            return True
        else:
            log.error("❌ zrok environment is NOT enabled")
            safe_print_stderr("❌ zrok environment is NOT enabled")
            return False
    except Exception as e:
        log.error("❌ Error checking zrok status: %s", e)
        safe_print_stderr(f"❌ Error checking zrok status: {e}")
        return False


def enable_zrok() -> None:
    """Guide user through zrok enable."""
    log.info("\n🔧 Zrok2 Repair Tool")
    log.info("=" * 50)
    safe_print("\n🔧 Zrok2 Repair Tool")
    safe_print("=" * 50)

    if not check_zrok_installation():
        log.info("\n📥 Please download zrok from:")
        log.info("   https://github.com/openziti/zrok/releases")
        log.info("\nAfter downloading, add it to your PATH and run this tool again.")
        safe_print("\n📥 Please download zrok from:")
        safe_print("   https://github.com/openziti/zrok/releases")
        safe_print("\nAfter downloading, add it to your PATH and run this tool again.")
        return

    if check_zrok_enabled():
        log.info("\n✅ Everything looks good! You can now use Zrok2 tunnel.")
        safe_print("\n✅ Everything looks good! You can now use Zrok2 tunnel.")
        return

    log.info("\n📝 To enable zrok, you need a token.")
    log.info("   1. Go to https://zrok.io and sign up")
    log.info("   2. Get your enable token from the dashboard")
    log.info("   3. Run: zrok enable <YOUR_TOKEN>")
    log.info("\nOr run this command now:")
    safe_print("\n📝 To enable zrok, you need a token.")
    safe_print("   1. Go to https://zrok.io and sign up")
    safe_print("   2. Get your enable token from the dashboard")
    safe_print("   3. Run: zrok enable <YOUR_TOKEN>")
    safe_print("\nOr run this command now:")

    token = input("\nEnter your zrok enable token (or press Enter to skip): ").strip()
    if token:
        try:
            result = subprocess.run(
                ["zrok", "enable", token],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                log.info("✅ zrok enabled successfully!")
                safe_print("✅ zrok enabled successfully!")
            else:
                log.error("❌ Failed to enable: %s", result.stderr)
                safe_print_stderr(f"❌ Failed to enable: {result.stderr}")
        except Exception as e:
            log.error("❌ Error: %s", e)
            safe_print_stderr(f"❌ Error: {e}")


def main():
    enable_zrok()
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
