#!/usr/bin/env bash
# ================================================================
# AnywhereInput - Universal Tunnel Launcher (Linux/macOS) - Creator: Z-Hussein
# Supports: Cloudflare Tunnel, Pinggy, Zrok2, ngrok
# ================================================================

set -e

cd "$(dirname "$0")"

echo ""
echo "================================================================"
echo " AnywhereInput - Remote Access Launcher - Creator: Z-Hussein"
echo "================================================================"
echo ""

# Find Python
PYCMD=""
if [ -f "./.venv/bin/python" ]; then
    PYCMD="./.venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYCMD="python3"
elif command -v python &> /dev/null; then
    PYCMD="python"
fi

if [ -z "$PYCMD" ]; then
    echo "ERROR: Python 3.9+ was not found."
    echo "Please install Python and ensure it's on your PATH."
    echo "Download: https://www.python.org/downloads/"
    exit 1
fi

echo "[*] Python found: $PYCMD"
echo ""

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment..."
    "$PYCMD" -m venv .venv
fi

source .venv/bin/activate

# Install dependencies
echo "[*] Installing dependencies..."
"$PYCMD" -m pip install -q -r requirements.txt 2>/dev/null || true

# Provider Selection Menu
while true; do
    echo ""
    echo "================================================================"
    echo " Choose your tunnel provider:"
    echo "================================================================"
    echo ""
    echo " [1] Cloudflare Tunnel  - FREE, no account, fastest globally"
    echo " [2] Pinggy.io          - FREE, uses SSH, no install needed"
    echo " [3] Zrok2              - FREE, open source, zero-trust"
    echo " [4] ngrok              - Free tier, requires account"
    echo ""
    echo " [Q] Quit"
    echo ""
    echo "================================================================"
    echo ""

    read -rp "Enter choice (1-4, or Q): " choice

    case "$choice" in
        1)
            echo ""
            echo "[*] Launching with Cloudflare Tunnel..."
            "$PYCMD" launch_with_tunnel.py --provider cloudflare "$@"
            break
            ;;
        2)
            echo ""
            echo "[*] Launching with Pinggy..."
            "$PYCMD" launch_with_tunnel.py --provider pinggy "$@"
            break
            ;;
        3)
            echo ""
            echo "[*] Launching with Zrok2..."
            "$PYCMD" launch_with_tunnel.py --provider zrok2 "$@"
            break
            ;;
        4)
            echo ""
            echo "[*] Launching with ngrok..."
            "$PYCMD" launch_with_tunnel.py --provider ngrok "$@"
            break
            ;;
        [Qq])
            exit 0
            ;;
        *)
            echo "[!] Invalid choice. Please try again."
            ;;
    esac
done
