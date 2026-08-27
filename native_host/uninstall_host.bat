@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   FTODE - Native Host Uninstaller
echo   Finally that online downloader extension
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"

echo [*] Unregistering Native Host from Windows Registry...
python "%SCRIPT_DIR%host.py" --uninstall

if errorlevel 1 (
    echo [x] Python unregistration failed. Removing registry keys directly...
    reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
    reg delete "HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
    reg delete "HKCU\Software\Chromium\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
    reg delete "HKCU\Software\Mozilla\NativeMessagingHosts\com.ftode.host" /f >nul 2>&1
    echo [v] Registry keys removed successfully!
)

echo.
echo ===================================================
echo   Native Host Uninstalled Successfully!
echo ===================================================
echo.
echo To remove the extension from your browser:
echo 1. Right-click the FTODE icon in your browser toolbar.
echo 2. Click "Remove from Chrome" / "Remove from Edge" / "Remove Extension".
echo.
pause
