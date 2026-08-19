@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   FTODE - 1-Click Native Host Setup
echo   Finally that online downloader extension
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "MANIFEST_PATH=%SCRIPT_DIR%com.ftode.host.json"

echo [*] Registering Native Host in Windows Registry...
python "%SCRIPT_DIR%host.py" --install

if errorlevel 1 (
    echo [x] Python registration failed. Attempting direct registry write...
    set "REG_KEY_CHROME=HKCU\Software\Google\Chrome\NativeMessagingHosts\com.ftode.host"
    set "REG_KEY_EDGE=HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.ftode.host"
    set "REG_KEY_CHROMIUM=HKCU\Software\Chromium\NativeMessagingHosts\com.ftode.host"
    set "REG_KEY_MOZILLA=HKCU\Software\Mozilla\NativeMessagingHosts\com.ftode.host"
    set "FIREFOX_MANIFEST_PATH=%SCRIPT_DIR%com.ftode.host-firefox.json"
    reg add "!REG_KEY_CHROME!" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f >nul 2>&1
    reg add "!REG_KEY_EDGE!" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f >nul 2>&1
    reg add "!REG_KEY_CHROMIUM!" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f >nul 2>&1
    reg add "!REG_KEY_MOZILLA!" /ve /t REG_SZ /d "!FIREFOX_MANIFEST_PATH!" /f >nul 2>&1
    if errorlevel 1 (
        echo [x] Registry write failed. Please check permissions.
    ) else (
        echo [v] Registry keys added successfully for Chrome, Edge, Opera, and Firefox!
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
