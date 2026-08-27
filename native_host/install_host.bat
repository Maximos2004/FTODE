@echo off
setlocal enabledelayedexpansion

REM ---------------------------------------------------------
REM Check if Python is installed and accessible
REM ---------------------------------------------------------
python -c "import sys; assert sys.version_info >= (3, 7)" >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        goto :python_missing
    )
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
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

:python_missing
color 0C 2>nul
cls
echo ==============================================================================
echo.
echo   #####  #   # ##### #   #  ###  #   #
echo   #   #   # #    #   #   # #   # ##  #
echo   #####    #     #   ##### #   # # # #
echo   #        #     #   #   # #   # #  ##
echo   #        #     #   #   #  ###  #   #
echo.
echo   #   #  ###  #####   ### #   #  ### #####   ###  #     #     ##### ####
echo   ##  # #   #   #      #  ##  # #      #    #   # #     #     #     #   #
echo   # # # #   #   #      #  # # #  ###   #    ##### #     #     ###   #   #
echo   #  ## #   #   #      #  #  ##     #  #    #   # #     #     #     #   #
echo   #   #  ###    #     ### #   #  ###   #    #   # ##### ##### ##### ####
echo.
echo ==============================================================================
echo  [X] FATAL ERROR: PYTHON IS NOT INSTALLED OR NOT IN PATH
echo ==============================================================================
echo.
echo  FTODE requires Python 3.8 or newer to run the background downloader engine.
echo.
echo  ==========================================================================
echo  HOW TO INSTALL PYTHON:
echo  ==========================================================================
echo  1. Download Python from: https://www.python.org/downloads/
echo     (or install Python from the Microsoft Store)
echo.
echo  2. CRITICAL STEP DURING INSTALLATION:
echo     [IMPORTANT] Make sure to CHECK the box at the bottom of the installer:
echo         [X] Add python.exe to PATH
echo.
echo  3. After Python finishes installing, run this Setup again.
echo  ==========================================================================
echo.
set /p "OPEN_PY=Would you like to open the Python download page now? (Y/N): "
if /i "!OPEN_PY!"=="Y" (
    start https://www.python.org/downloads/
)
echo.
pause
exit /b 1


