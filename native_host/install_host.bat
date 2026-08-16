@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo     Max's Downloader - 1-Click Native Host Setup
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "MANIFEST_PATH=%SCRIPT_DIR%com.maxsdownloader.host.json"

echo [*] Registering Native Host in Windows Registry...
python "%SCRIPT_DIR%host.py" --install

if errorlevel 1 (
    echo [x] Python registration failed. Attempting direct registry write...
    set "REG_KEY=HKCU\Software\Google\Chrome\NativeMessagingHosts\com.maxsdownloader.host"
    reg add "!REG_KEY!" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f
    if errorlevel 1 (
        echo [x] Registry write failed. Please check permissions.
    ) else (
        echo [v] Registry key added successfully via Windows Registry!
    )
)

echo.
echo [*] Checking bundled yt-dlp & FFmpeg binaries...
python "%SCRIPT_DIR%host.py" --bootstrap

echo.
echo ===================================================
echo     Setup Complete! Extension is ready to use.
echo ===================================================
echo.
pause
