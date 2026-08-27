#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

# Verify python3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "\033[1;31m"
    echo "=============================================================================="
    echo " [X] FATAL ERROR: python3 is not installed or not in PATH!"
    echo "=============================================================================="
    echo " FTODE requires Python 3.8+ to download media and run the backend host."
    echo ""
    echo " Please install Python 3 and FFmpeg using your package manager:"
    echo "   Ubuntu / Debian / Mint:  sudo apt install python3 ffmpeg"
    echo "   Arch / Manjaro:         sudo pacman -S python ffmpeg"
    echo "   Fedora / RHEL:          sudo dnf install python3 ffmpeg"
    echo "   openSUSE:               sudo zypper install python3 ffmpeg"
    echo "=============================================================================="
    echo -e "\033[0m"
    exit 1
fi

if [ -f "$DIR/_backend/install_host.sh" ]; then
    bash "$DIR/_backend/install_host.sh"
elif [ -f "$DIR/native_host/install_host.sh" ]; then
    bash "$DIR/native_host/install_host.sh"
else
    echo "[x] Setup files not found."
    exit 1
fi

