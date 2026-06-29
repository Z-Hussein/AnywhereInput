"""Zrok2 diagnostic and repair tool."""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def check_zrok_installation() -> bool:
    """Check if zrok is properly installed."""
    zrok_path = shutil.which("zrok") or shutil.which("zrok2")
    if zrok_path:
        print(f"✅ zrok found: {zrok_path}")
        return True
    print("❌ zrok not found in PATH")
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
            print("✅ zrok environment is enabled")
            return True
        else:
            print("❌ zrok environment is NOT enabled")
            return False
    except Exception as e:
        print(f"❌ Error checking zrok status: {e}")
        return False


def enable_zrok() -> None:
    """Guide user through zrok enable."""
    print("\n🔧 Zrok2 Repair Tool")
    print("=" * 50)

    if not check_zrok_installation():
        print("\n📥 Please download zrok from:")
        print("   https://github.com/openziti/zrok/releases")
        print("\nAfter downloading, add it to your PATH and run this tool again.")
        return

    if check_zrok_enabled():
        print("\n✅ Everything looks good! You can now use Zrok2 tunnel.")
        return

    print("\n📝 To enable zrok, you need a token.")
    print("   1. Go to https://zrok.io and sign up")
    print("   2. Get your enable token from the dashboard")
    print("   3. Run: zrok enable <YOUR_TOKEN>")
    print("\nOr run this command now:")

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
                print("✅ zrok enabled successfully!")
            else:
                print(f"❌ Failed to enable: {result.stderr}")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    enable_zrok()
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
