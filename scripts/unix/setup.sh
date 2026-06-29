#!/bin/bash
set -e

echo "AnywhereInput - Linux/macOS Setup"
echo "=================================="

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.9+"
    exit 1
fi

python3 --version

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo ""
echo "Setup complete! Run './scripts/linux/run.sh' to start."
