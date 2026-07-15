"""Zrok2 diagnostic and repair tool."""

import subprocess
import shutil
from anywhereinput import safe_print, safe_print_stderr


def check_zrok_installation() -> bool:
    """Check if zrok is properly installed."""
    zrok_path = shutil.which("zrok") or shutil.which("zrok2")
    if zrok_path:
        safe_print(f"\u2705 zrok found: {zrok_path}")
        return True
    safe_print_stderr("\u274c zrok not found in PATH")
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
            safe_print("\u2705 zrok environment is enabled")
            return True
        else:
            safe_print_stderr("\u274c zrok environment is NOT enabled")
            return False
    except Exception as e:
        safe_print_stderr(f"\u274c Error checking zrok status: {e}")
        return False


def enable_zrok() -> None:
    """Guide user through zrok enable."""
    safe_print("\n\U0001f527 Zrok2 Repair Tool")
    safe_print("=" * 50)

    if not check_zrok_installation():
        safe_print("\n\U0001f4e5 Please download zrok from:")
        safe_print("   https://github.com/openziti/zrok/releases")
        safe_print("\nAfter downloading, add it to your PATH and run this tool again.")
        return

    if check_zrok_enabled():
        safe_print("\n\u2705 Everything looks good! You can now use Zrok2 tunnel.")
        return

    safe_print("\n\U0001f4dd To enable zrok, you need a token.")
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
                safe_print("\u2705 zrok enabled successfully!")
            else:
                safe_print_stderr(f"\u274c Failed to enable: {result.stderr}")
        except Exception as e:
            safe_print_stderr(f"\u274c Error: {e}")


def main():
    enable_zrok()
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
