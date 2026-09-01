@echo off
setlocal enabledelayedexpansion

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

if not defined PY_CMD (
    echo [*] Python 3.8+ was not detected on your system.
    echo [*] Downloading and installing Python automatically...
    echo.

    set "FTODE_DATA=%LOCALAPPDATA%\FTODE"
    if not exist "!FTODE_DATA!" mkdir "!FTODE_DATA!" >nul 2>&1

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "$arch = if ([IntPtr]::Size -eq 8) { 'amd64' } else { 'win32' }; " ^
        "$installerUrl = \"https://www.python.org/ftp/python/3.12.8/python-3.12.8-$arch.exe\"; " ^
        "$installerPath = Join-Path $env:LOCALAPPDATA 'FTODE\.ftode_python_installer.exe'; " ^
        "Write-Host '[*] Downloading Python from python.org...' -ForegroundColor Cyan; " ^
        "(New-Object System.Net.WebClient).DownloadFile($installerUrl, $installerPath); " ^
        "if (-not (Test-Path $installerPath) -or (Get-Item $installerPath).Length -lt 20000000) { " ^
        "    Write-Host '[X] Python installer download failed or file is incomplete.' -ForegroundColor Red; exit 1; " ^
        "}; " ^
        "Write-Host '[*] Installing Python (with PATH configured)...' -ForegroundColor Cyan; " ^
        "$proc = Start-Process -FilePath $installerPath -ArgumentList '/passive', 'InstallAllUsers=0', 'PrependPath=1', 'Include_test=0', 'SimpleInstall=1' -Wait -PassThru; " ^
        "if ($proc.ExitCode -ne 0) { exit $proc.ExitCode }"

    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;!PATH!"
    for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;!PATH!"

    python -c "import sys; assert sys.version_info >= (3, 8)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
    ) else (
        py -3 -c "import sys; assert sys.version_info >= (3, 8)" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD=py -3"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
            set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
            set "PY_CMD=python"
        ) else (
            echo.
            echo [!] Automated Python installation could not be completed.
            echo     Please install Python from: https://www.python.org/downloads/
            echo     (Make sure to check "Add python.exe to PATH" during installation)
            echo.
            pause
            exit /b 1
        )
    )
)

echo ===================================================
echo   FTODE - 1-Click Native Host Setup
echo   Finally that online downloader extension
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "MANIFEST_PATH=%SCRIPT_DIR%com.ftode.host.json"

echo [*] Registering Native Host in Windows Registry...
!PY_CMD! "%SCRIPT_DIR%host.py" --install

if errorlevel 1 (
    echo [*] Python registration warning. Attempting direct registry write...
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
        color 0C 2>nul
        echo [X] Registry write failed. Please check permissions.
        echo.
        pause
        exit /b 1
    ) else (
        echo [v] Registry keys added successfully for Chrome, Edge, Opera, and Firefox
    )
)

echo.
echo [*] Checking bundled yt-dlp and FFmpeg binaries...
!PY_CMD! "%SCRIPT_DIR%host.py" --bootstrap

echo.
echo ===================================================
echo     Setup Complete - Extension is ready to use.
echo ===================================================
echo.
pause
exit /b 0
