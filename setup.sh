#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$DIR/_backend/install_host.sh" ]; then
    bash "$DIR/_backend/install_host.sh"
elif [ -f "$DIR/native_host/install_host.sh" ]; then
    bash "$DIR/native_host/install_host.sh"
else
    echo "[x] Setup files not found."
    exit 1
fi
