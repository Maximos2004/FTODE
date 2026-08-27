@echo off
title FTODE - Uninstaller
setlocal enabledelayedexpansion

echo ===================================================
echo   FTODE - 1-Click Uninstaller
echo   Finally that online downloader extension
echo ===================================================
echo.

set "TARGET_DIR=%LOCALAPPDATA%\FTODE"

echo [*] Stopping any active FTODE tasks...
taskkill /f /im yt-dlp.exe >nul 2>&1
taskkill /f /im ffmpeg.exe >nul 2>&1

echo [*] Removing FTODE Native Messaging Registry keys...
reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\Software\Chromium\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\Software\Mozilla\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1

if exist "%TARGET_DIR%" (
    echo [*] Removing installed backend files from %TARGET_DIR%...
    rmdir /s /q "%TARGET_DIR%" >nul 2>&1
)

echo.
echo ===================================================
echo     FTODE Native Host Uninstalled Successfully!
echo ===================================================
echo.
echo Final Step:
echo Right-click the FTODE icon in your browser toolbar
echo and click "Remove from Chrome" / "Remove from Edge".
echo.
pause
