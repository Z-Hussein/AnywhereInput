#!/bin/bash
# Ensure proper terminal capabilities (fixes TERM=dumb hanging issues)
export TERM="${TERM:-xterm}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get the project root (two levels up from scripts/linux)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# CRITICAL: cd to project root before anything else
cd "$PROJECT_ROOT"

clear 2>/dev/null || true

print_banner() {
    echo -e "${CYAN}"
    echo "░█▀█░█▀█░█░█░█ ░ █░█░█░█▀▀░█▀▄░█▀▀░▀█▀░█▀█░█▀█░█░█░▀█▀"
    echo "░█▀█░█░█░░█░░█▄▀▄█░█▀█░█▀▀░█▀▄░█▀▀░░█░░█░█░█▀▀░█░█░░█░"
    echo "░▀░▀░▀░▀░░▀░░▀░ ░▀ ▀░▀░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░░▀░.com"
    echo "  AnywhereInput v1.0.0 — Remote Control Your PC"
    echo "        by AnywhereInput.com Github: @Z-Hussein"
    echo -e "${NC}"
}


# ── Kill only project-specific tunnel processes ──────────────────────────────
kill_project_tunnels() {
    # Only kill processes that match our specific port patterns, not all zrok/ngrok
    local port="${AI_PORT:-8008}"
    for pid in $(pgrep -f "zrok share.*localhost:${port}" 2>/dev/null || true); do
        kill "$pid" 2>/dev/null || true
    done
    for pid in $(pgrep -f "ngrok http.*${port}" 2>/dev/null || true); do
        kill "$pid" 2>/dev/null || true
    done
    for pid in $(pgrep -f "cloudflared tunnel.*localhost:${port}" 2>/dev/null || true); do
        kill "$pid" 2>/dev/null || true
    done
    sleep 0.5
}

kill_project_tunnels

# ── Auto-setup: install deps + package if first run ──────────────────────
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/anywhereinput" ]; then
    echo -e "${YELLOW}First run detected. Setting up AnywhereInput...${NC}"
    echo ""

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: Python 3 not found. Please install Python 3.9+${NC}"
        exit 1
    fi

    python3 --version
    echo ""

    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip >/dev/null 2>&1
    pip install -e . >/dev/null 2>&1

    echo -e "${GREEN}✓ Setup complete!${NC}"
    echo ""
fi

source .venv/bin/activate || { echo -e "${RED}ERROR: Failed to activate virtual environment${NC}"; exit 1; }

# Resolve the anywhereinput executable (use full path as fallback)
ANYWHEREINPUT_CMD=$(command -v anywhereinput 2>/dev/null || echo "$PROJECT_ROOT/.venv/bin/anywhereinput")

# ── Tunnel availability helpers ────────────────────────────────────────────
check_cloudflare() {
    [ -f "./cloudflared" ] || command -v cloudflared &>/dev/null || true
}

check_tailscale() {
    command -v tailscale &>/dev/null && tailscale status --json &>/dev/null
}

check_pinggy() {
    command -v ssh &>/dev/null
}

check_zrok() {
    command -v zrok &>/dev/null || command -v zrok2 &>/dev/null
}

check_ngrok() {
    command -v ngrok &>/dev/null
}

show_menu() {
    echo ""
    local cf_ok ts_ok pg_ok zrok_ok ngrok_ok

    cf_ok=$(check_cloudflare && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")
    ts_ok=$(check_tailscale && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}?${NC}")
    pg_ok=$(check_pinggy && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}?${NC}")
    zrok_ok=$(check_zrok && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}?${NC}")
    ngrok_ok=$(check_ngrok && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}?${NC}")

    echo -e "Select tunnel provider:"
    echo -e "  [1] Cloudflare Tunnel (Recommended) ${cf_ok}"
    echo -e "  [2] Tailscale (tailnet P2P) ${ts_ok}"
    echo -e "  ${CYAN}Both devices must be on the same tailnet${NC}"
    echo -e "  [3] Pinggy.io ${pg_ok}"
    echo -e "  ${CYAN}Uses your existing SSH client${NC}"
    echo -e "  [4] Zrok2 ${zrok_ok}"
    echo -e "  [5] ngrok ${ngrok_ok}"
    echo -e "  [6] Local only"
    echo -e "  [Q-q] Quit"
    echo ""
    read -p "Enter choice: " choice

    case $choice in
        1) $ANYWHEREINPUT_CMD --tunnel cloudflare ;;
        2) $ANYWHEREINPUT_CMD --tunnel tailscale ;;
        3) $ANYWHEREINPUT_CMD --tunnel pinggy ;;
        4) $ANYWHEREINPUT_CMD --tunnel zrok2 ;;
        5) $ANYWHEREINPUT_CMD --tunnel ngrok ;;
        6) $ANYWHEREINPUT_CMD ;;
        q|Q) exit 0 ;;
        *) show_menu ;;
    esac
}

# ── TTY detection: auto-launch if no real terminal ───────────────────────
if [ -t 0 ]; then
    # Real terminal — show interactive menu
    print_banner
    show_menu
else
    # No TTY — auto-launch cloudflare tunnel
    print_banner
    echo -e "${CYAN}No terminal input available — starting Cloudflare Tunnel...${NC}"
    $ANYWHEREINPUT_CMD --tunnel cloudflare 2>&1
    exit $?
fi
