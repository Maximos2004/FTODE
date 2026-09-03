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
reg delete "HKCU\Software\Opera Software\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\Software\Opera Software\Opera GX\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\Software\Opera Software\Opera Stable\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
reg delete "HKCU\Software\Mozilla\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1

set "PY_INSTALLER="
if exist "%TARGET_DIR%\.ftode_python_installer.exe" set "PY_INSTALLER=%TARGET_DIR%\.ftode_python_installer.exe"
if exist "%~dp0native_host\.ftode_python_installer.exe" set "PY_INSTALLER=%~dp0native_host\.ftode_python_installer.exe"

if defined PY_INSTALLER (
    echo [*] Python was automatically installed by FTODE Setup.
    echo [*] Uninstalling Python from your system...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$proc = Start-Process -FilePath '!PY_INSTALLER!' -ArgumentList '/uninstall', '/passive' -Wait -PassThru; " ^
        "Remove-Item '!PY_INSTALLER!' -Force -ErrorAction SilentlyContinue"
    echo [v] Python has been uninstalled successfully.
    echo.
) else (
    echo [*] Python was not installed by FTODE (leaving existing Python installation intact).
)

if exist "%TARGET_DIR%" (
    echo [*] Removing installed backend files and tools (yt-dlp, FFmpeg) from %TARGET_DIR%...
    rmdir /s /q "%TARGET_DIR%" >nul 2>&1
)

if exist "%~dp0native_host\bin" (
    echo [*] Cleaning up downloaded tools from repository bin folder...
    rmdir /s /q "%~dp0native_host\bin" >nul 2>&1
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
