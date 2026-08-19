@echo off
REM Finally that online downloader extension (FTODE) - Native Messaging Host Launcher
REM Ensures Python runs in unbuffered binary mode for browser stdio
python -u "%~dp0host.py" %*
