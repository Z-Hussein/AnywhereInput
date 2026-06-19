#!/bin/bash

# Remote Mouse Controller - Linux Setup Script
# This script sets up Python virtual environment and installs dependencies

set -e
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}  Remote Mouse Controller - Linux Setup${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""

# Detect package manager and OS
INSTALL_CMD=""
OS=""

if command -v apt-get &> /dev/null; then
    INSTALL_CMD="sudo apt-get"
    OS="Ubuntu/Debian"
elif command -v dnf &> /dev/null; then
    INSTALL_CMD="sudo dnf"
    OS="Fedora/RHEL"
elif command -v yum &> /dev/null; then
    INSTALL_CMD="sudo yum"
    OS="CentOS/RHEL"
elif command -v pacman &> /dev/null; then
    INSTALL_CMD="sudo pacman -S"
    OS="Arch Linux"
elif command -v brew &> /dev/null; then
    INSTALL_CMD="brew"
    OS="macOS"
fi

echo -e "${GREEN}Detected OS: $OS${NC}"
echo ""

# Try to find Python
PYCMD=""
if command -v python3 &> /dev/null; then
    PYCMD="python3"
elif command -v python &> /dev/null; then
    PYCMD="python"
fi

if [ -z "$PYCMD" ]; then
    echo -e "${YELLOW}Python not found. Attempting to install...${NC}"
    echo ""
    
    if [ -z "$INSTALL_CMD" ]; then
        echo -e "${RED}ERROR: Could not detect package manager.${NC}"
        echo "Please install Python 3.9+ manually and run this script again."
        exit 1
    fi
    
    # Install Python based on OS
    case "$OS" in
        Ubuntu/Debian)
            echo "Installing Python 3 and venv..."
            $INSTALL_CMD update
            $INSTALL_CMD install -y python3 python3-venv python3-pip
            ;;
        Fedora/RHEL|CentOS/RHEL)
            echo "Installing Python 3 and venv..."
            $INSTALL_CMD install -y python3 python3-venv python3-pip
            ;;
        Arch\ Linux)
            echo "Installing Python 3..."
            $INSTALL_CMD python
            ;;
        macOS)
            echo "Installing Python 3..."
            $INSTALL_CMD install python@3.11
            ;;
        *)
            echo -e "${RED}ERROR: Unsupported OS for automatic installation.${NC}"
            echo "Please install Python 3.9+ manually."
            exit 1
            ;;
    esac
    
    PYCMD="python3"
fi

echo ""
echo -e "${GREEN}Python found: $($PYCMD --version)${NC}"
echo ""

echo "Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    $PYCMD -m venv .venv
fi

if [ ! -f ".venv/bin/activate" ]; then
    echo -e "${RED}ERROR: Failed to create virtual environment${NC}"
    exit 1
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing required packages..."
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

echo ""
echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}===================================================${NC}"
echo ""
echo "To start the server, run one of these commands:"
echo ""
echo -e "${BLUE}  For local network use:${NC}"
echo "    ./start_with_ngrok.sh"
echo "    python secure_mouse_server.py"
echo ""
echo -e "${BLUE}  For remote access (requires ngrok):${NC}"
echo "    ./start_with_ngrok.sh"
echo "    python launch_with_ngrok.py"
echo ""
echo -e "${GREEN}===================================================${NC}"
echo ""
