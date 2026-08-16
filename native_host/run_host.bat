@echo off
REM Max's Downloader - Native Messaging Host Launcher
REM Ensures Python runs in unbuffered binary mode for Chrome stdio
python -u "%~dp0host.py" %*
