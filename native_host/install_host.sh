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

echo "==================================================="
echo "  FTODE - 1-Click Native Host Setup (Linux)"
echo "  Finally that online downloader extension"
echo "==================================================="
echo ""

chmod +x "$DIR/host.py" "$DIR/run_host.sh" 2>/dev/null || true

echo "[*] Registering Native Messaging Host for Linux browsers..."
python3 "$DIR/host.py" --install

echo ""
echo "[*] Checking yt-dlp & FFmpeg dependencies..."
python3 "$DIR/host.py" --bootstrap

echo ""
echo "==================================================="
echo "    Setup Complete! Extension is ready to use."
echo "==================================================="
echo ""

