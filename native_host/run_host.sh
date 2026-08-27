#!/usr/bin/env bash
# FTODE Native Messaging Host Launcher for Linux
# Ensures Python runs in unbuffered binary mode for browser stdio
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 -u "$DIR/host.py" "$@"
