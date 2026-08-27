@echo off
title FTODE - Setup
setlocal enabledelayedexpansion

cd /d "%~dp0"

if exist "%~dp0_backend\install_host.bat" (
    cd /d "%~dp0_backend"
    call install_host.bat
) else if exist "%~dp0native_host\install_host.bat" (
    cd /d "%~dp0native_host"
    call install_host.bat
) else (
    echo [x] Setup files not found.
    pause
)
