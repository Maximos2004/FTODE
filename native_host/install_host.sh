#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

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
