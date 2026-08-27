@echo off
title FTODE - Setup
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ---------------------------------------------------------
REM Check if Python is installed and accessible
REM ---------------------------------------------------------
python -c "import sys; assert sys.version_info >= (3, 7)" >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        goto :python_missing
    )
)

if exist "%~dp0_backend\install_host.bat" (
    cd /d "%~dp0_backend"
    call install_host.bat
) else if exist "%~dp0native_host\install_host.bat" (
    cd /d "%~dp0native_host"
    call install_host.bat
) else (
    color 0C 2>nul
    echo.
    echo ===================================================
    echo  [X] Setup files not found.
    echo ===================================================
    echo.
    pause
    exit /b 1
)
exit /b %ERRORLEVEL%

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

