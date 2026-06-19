#!/bin/bash

# Remote Mouse Controller - Linux ngrok Launcher
# This script sets up the environment and starts the server with ngrok

set -e
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Try to find Python: prefer local venv, then python3, then python
PYCMD=""
if [ -f ".venv/bin/python" ]; then
    PYCMD=".venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYCMD="python3"
elif command -v python &> /dev/null; then
    PYCMD="python"
fi

if [ -z "$PYCMD" ]; then
    echo -e "${RED}ERROR: Python 3.9+ was not found on this system.${NC}"
    echo "Please install Python 3 and ensure it's on your PATH:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-venv"
    echo "  Fedora/RHEL: sudo dnf install python3 python3-venv"
    echo "  macOS: brew install python3"
    exit 1
fi

echo ""
echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    $PYCMD -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing required packages..."
# Don't swallow pip failures — surface them instead of letting the
# launcher crash later with a confusing import error.
python -m pip install -q -r requirements.txt
python -c "import pyautogui, aiohttp, requests" || {
    echo -e "${RED}ERROR: Required Python packages failed to install.${NC}"
    exit 1
}

echo ""
echo "Searching for ngrok executable..."
NGROK_PATH=""

# Check current directory
if [ -f "./ngrok" ]; then
    NGROK_PATH="./ngrok"
fi

# Check common Linux locations
if [ -z "$NGROK_PATH" ]; then
    for path in \
        "/usr/local/bin/ngrok" \
        "/usr/bin/ngrok" \
        "$HOME/.local/bin/ngrok" \
        "$HOME/ngrok" \
        "$HOME/Downloads/ngrok" \
        "/opt/ngrok/ngrok"
    do
        if [ -f "$path" ]; then
            NGROK_PATH="$path"
            break
        fi
    done
fi

# Try 'which' command
if [ -z "$NGROK_PATH" ]; then
    if command -v ngrok &> /dev/null; then
        NGROK_PATH="$(which ngrok)"
    fi
fi

if [ -n "$NGROK_PATH" ]; then
    echo -e "${GREEN}Found ngrok: $NGROK_PATH${NC}"
else
    echo -e "${YELLOW}WARNING: ngrok not found. The launcher will prompt for instructions.${NC}"
fi

echo "Starting ngrok launcher..."
if [ -n "$NGROK_PATH" ]; then
    python launch_with_ngrok.py --ngrok-path "$NGROK_PATH" "$@"
else
    python launch_with_ngrok.py "$@"
fi
