#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==================================================="
echo "  FTODE - Native Host Uninstaller (Linux)"
echo "  Finally that online downloader extension"
echo "==================================================="
echo ""

python3 "$DIR/host.py" --uninstall

echo ""
echo "==================================================="
echo "    FTODE Native Host Uninstalled Successfully!"
echo "==================================================="
echo ""
