#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$DIR/_backend/uninstall_host.sh" ]; then
    bash "$DIR/_backend/uninstall_host.sh"
elif [ -f "$DIR/native_host/uninstall_host.sh" ]; then
    bash "$DIR/native_host/uninstall_host.sh"
else
    python3 "$DIR/native_host/host.py" --uninstall 2>/dev/null || true
fi
