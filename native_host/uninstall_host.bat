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

set "TARGET_DIR=%LOCALAPPDATA%\FTODE"
set "PY_INSTALLER="
if exist "%TARGET_DIR%\.ftode_python_installer.exe" set "PY_INSTALLER=%TARGET_DIR%\.ftode_python_installer.exe"
if exist "%SCRIPT_DIR%.ftode_python_installer.exe" set "PY_INSTALLER=%SCRIPT_DIR%.ftode_python_installer.exe"

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

if exist "%SCRIPT_DIR%bin" (
    echo [*] Cleaning up downloaded tools from %SCRIPT_DIR%bin...
    rmdir /s /q "%SCRIPT_DIR%bin" >nul 2>&1
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
