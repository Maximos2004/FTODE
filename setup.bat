@echo off
title FTODE - Setup
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ===================================================
echo   FTODE - 1-Click Setup
echo   Finally that online downloader extension
echo ===================================================
echo.

REM ---------------------------------------------------------
REM Check if Python is installed and accessible
REM ---------------------------------------------------------
set "PY_CMD="
python -c "import sys; assert sys.version_info >= (3, 8)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
) else (
    py -3 -c "import sys; assert sys.version_info >= (3, 8)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3"
    )
)

if defined PY_CMD (
    echo [v] Python is installed and ready.
    goto :run_installer
)

REM ---------------------------------------------------------
REM Python not detected - Download & Install Automatically
REM ---------------------------------------------------------
echo [*] Python 3.8+ was not detected on your system.
echo [*] Downloading and installing Python automatically...
echo.

    set "FTODE_DATA=%LOCALAPPDATA%\FTODE"
    if not exist "!FTODE_DATA!" mkdir "!FTODE_DATA!" >nul 2>&1

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$arch = if ([IntPtr]::Size -eq 8) { 'amd64' } else { 'win32' }; " ^
        "$installerUrl = \"https://www.python.org/ftp/python/3.12.8/python-3.12.8-$arch.exe\"; " ^
        "$installerPath = Join-Path $env:LOCALAPPDATA 'FTODE\.ftode_python_installer.exe'; " ^
        "Write-Host '[*] Downloading Python from python.org...' -ForegroundColor Cyan; " ^
        "(New-Object System.Net.WebClient).DownloadFile($installerUrl, $installerPath); " ^
        "Write-Host '[*] Installing Python (with PATH configured)...' -ForegroundColor Cyan; " ^
        "$proc = Start-Process -FilePath $installerPath -ArgumentList '/passive', 'InstallAllUsers=0', 'PrependPath=1', 'Include_test=0', 'SimpleInstall=1' -Wait -PassThru; " ^
        "if ($proc.ExitCode -ne 0) { exit $proc.ExitCode }"

REM Refresh environment PATH in current shell
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;!PATH!"
for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;!PATH!"

REM Re-verify Python
python -c "import sys; assert sys.version_info >= (3, 8)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    echo [v] Python installed successfully!
    echo.
    goto :run_installer
)

py -3 -c "import sys; assert sys.version_info >= (3, 8)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    echo [v] Python installed successfully!
    echo.
    goto :run_installer
)

REM Check default user AppData Python location if PATH didn't reload immediately
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
    set "PY_CMD=python"
    echo [v] Python located and configured!
    echo.
    goto :run_installer
)

echo.
echo [!] Automated Python installation could not be verified in the current session.
echo     Please install Python manually from: https://www.python.org/downloads/
echo     (Make sure to check "Add python.exe to PATH" during installation)
echo.
set /p "OPEN_PY=Would you like to open python.org in your browser? (Y/N): "
if /i "!OPEN_PY!"=="Y" start https://www.python.org/downloads/
echo.
pause
exit /b 1

:run_installer
if exist "%~dp0_backend\install_host.bat" (
    cd /d "%~dp0_backend"
    call install_host.bat
) else if exist "%~dp0native_host\install_host.bat" (
    cd /d "%~dp0native_host"
    call install_host.bat
) else (
    echo.
    echo ===================================================
    echo  [X] Setup files not found.
    echo ===================================================
    echo.
    pause
    exit /b 1
)
exit /b %ERRORLEVEL%
